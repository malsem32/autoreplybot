"""Vacation mode, quick phrases and AI replies (AGENTS.md 4.17)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.core import rate_limit as rate_limiting
from backend.core.rate_limit import rate_limit
from backend.core.timeutil import as_utc
from backend.core.uploads import delete_uploads
from backend.db.session import get_db
from backend.models.snippet import Snippet
from backend.models.telegram_account import TelegramAccount
from backend.models.user import User
from backend.schemas.assistant import (
    AiPreviewIn,
    AiPreviewOut,
    AiSettingsIn,
    AiSettingsOut,
    AwayIn,
    AwayOut,
    SnippetIn,
    SnippetListOut,
    SnippetOut,
    SnippetUpdate,
)
from backend.services import access, ai, away, pro
from backend.services.media import resolve_photos
from backend.services.snippets import FREE_MAX_SNIPPETS, PRO_MAX_SNIPPETS

router = APIRouter(prefix="/api", tags=["assistant"])

_assistant_rate_limit = rate_limit("assistant", limit=60, window_seconds=60)
# Each preview is a paid/limited call to the AI provider.
_ai_preview_rate_limit = rate_limit("ai_preview", limit=10, window_seconds=60)


async def _owner(db: AsyncSession, account: TelegramAccount) -> User:
    return await access.account_owner(db, account)


# --- Vacation mode (free) ---------------------------------------------------------


def _away_out(account: TelegramAccount) -> AwayOut:
    until = as_utc(account.away_until)
    return AwayOut(
        active=away.is_away(account, datetime.now(UTC)),
        until=until,
        text=account.away_text,
        preview=away.render_away_text(account.away_text, until, account.away_timezone)
        if until
        else account.away_text,
    )


@router.get("/away/{account_id}", response_model=AwayOut)
async def get_away(
    account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AwayOut:
    return _away_out(await access.get_account(db, user, account_id))


@router.put("/away/{account_id}", response_model=AwayOut)
async def set_away(
    account_id: int,
    payload: AwayIn,
    user: User = Depends(_assistant_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> AwayOut:
    account = await access.get_account(db, user, account_id)
    now = datetime.now(UTC)
    until = as_utc(payload.until)
    assert until is not None
    if until <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Дата возвращения уже прошла")
    if until > now + timedelta(days=away.MAX_AWAY_DAYS):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Отпуск — не дольше {away.MAX_AWAY_DAYS} дней"
        )
    account.away_until = until
    account.away_text = payload.text
    account.away_timezone = payload.timezone
    await db.commit()
    return _away_out(account)


@router.delete("/away/{account_id}", response_model=AwayOut)
async def stop_away(
    account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AwayOut:
    account = await access.get_account(db, user, account_id)
    account.away_until = None
    await db.commit()
    return _away_out(account)


# --- Quick phrases (3 free, unlimited with Pro) -----------------------------------


async def _snippet_limit(db: AsyncSession, account: TelegramAccount) -> int | None:
    return None if pro.has_access(await _owner(db, account)) else FREE_MAX_SNIPPETS


async def _get_snippet(db: AsyncSession, account_id: int, snippet_id: int) -> Snippet:
    snippet = await db.scalar(
        select(Snippet).where(Snippet.id == snippet_id, Snippet.account_id == account_id)
    )
    if snippet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Фраза не найдена")
    return snippet


async def _commit_snippet(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Фраза с таким сокращением уже есть") from exc


@router.get("/snippets/{account_id}", response_model=SnippetListOut)
async def list_snippets(
    account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> SnippetListOut:
    account = await access.get_account(db, user, account_id)
    rows = await db.execute(
        select(Snippet).where(Snippet.account_id == account_id).order_by(Snippet.shortcut)
    )
    return SnippetListOut(
        snippets=[SnippetOut.model_validate(s) for s in rows.scalars()],
        limit=await _snippet_limit(db, account),
    )


@router.post("/snippets/{account_id}", response_model=SnippetOut, status_code=201)
async def create_snippet(
    account_id: int,
    payload: SnippetIn,
    user: User = Depends(_assistant_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> SnippetOut:
    account = await access.get_account(db, user, account_id)
    owner = await _owner(db, account)
    count = await db.scalar(
        select(func.count()).select_from(Snippet).where(Snippet.account_id == account_id)
    )
    limit = PRO_MAX_SNIPPETS if pro.has_access(owner) else FREE_MAX_SNIPPETS
    if (count or 0) >= limit:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            f"Без Pro — до {FREE_MAX_SNIPPETS} быстрых фраз"
            if limit == FREE_MAX_SNIPPETS
            else f"Не больше {PRO_MAX_SNIPPETS} фраз",
        )
    snippet = Snippet(
        account_id=account_id,
        shortcut=payload.shortcut,
        text=payload.text,
        photo_paths=resolve_photos(payload.photos, owner),
    )
    db.add(snippet)
    await _commit_snippet(db)
    return SnippetOut.model_validate(snippet)


@router.patch("/snippets/{account_id}/{snippet_id}", response_model=SnippetOut)
async def update_snippet(
    account_id: int,
    snippet_id: int,
    payload: SnippetUpdate,
    user: User = Depends(_assistant_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> SnippetOut:
    account = await access.get_account(db, user, account_id)
    snippet = await _get_snippet(db, account_id, snippet_id)
    data = payload.model_dump(exclude_unset=True)
    old_photos = list(snippet.photo_paths or [])
    if "photos" in data:
        snippet.photo_paths = resolve_photos(data.pop("photos") or [], await _owner(db, account))
    for field, value in data.items():
        if value is not None:
            setattr(snippet, field, value)
    await _commit_snippet(db)
    delete_uploads(old_photos, keep=snippet.photo_paths)
    return SnippetOut.model_validate(snippet)


@router.delete("/snippets/{account_id}/{snippet_id}", status_code=204)
async def delete_snippet(
    account_id: int,
    snippet_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await access.get_account(db, user, account_id)
    snippet = await _get_snippet(db, account_id, snippet_id)
    photos = list(snippet.photo_paths or [])
    await db.delete(snippet)
    await db.commit()
    delete_uploads(photos)


# --- AI replies (Pro) -------------------------------------------------------------


async def _ai_settings(account: TelegramAccount, owner: User) -> AiSettingsOut:
    return AiSettingsOut(
        available=ai.is_configured(),
        knowledge=account.ai_knowledge,
        tone=account.ai_tone,
        daily_limit=ai.settings.ai_daily_limit,
        used_today=await ai.used_today(rate_limiting.get_redis(), owner.id),
    )


@router.get("/ai/{account_id}", response_model=AiSettingsOut)
async def get_ai_settings(
    account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AiSettingsOut:
    account = await access.get_account(db, user, account_id)
    return await _ai_settings(account, await _owner(db, account))


@router.put("/ai/{account_id}", response_model=AiSettingsOut)
async def update_ai_settings(
    account_id: int,
    payload: AiSettingsIn,
    user: User = Depends(_assistant_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> AiSettingsOut:
    account = await access.get_account(db, user, account_id)
    account.ai_knowledge = payload.knowledge
    account.ai_tone = payload.tone
    await db.commit()
    return await _ai_settings(account, await _owner(db, account))


@router.post("/ai/{account_id}/preview", response_model=AiPreviewOut)
async def preview_ai_reply(
    account_id: int,
    payload: AiPreviewIn,
    user: User = Depends(_ai_preview_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> AiPreviewOut:
    """Shows what the AI would answer to a sample client message. Counts
    against the owner's daily AI limit like a real reply."""
    account = await access.get_account(db, user, account_id)
    owner = await _owner(db, account)
    if not pro.has_access(owner):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "ИИ-ответы — функция Pro")
    if not ai.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ИИ пока не подключён на сервере")
    redis = rate_limiting.get_redis()
    if not await ai.take_quota(redis, owner.id):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Дневной лимит ИИ ({ai.settings.ai_daily_limit}) исчерпан — завтра обновится",
        )
    answer = await ai.generate_reply(
        account.ai_knowledge,
        account.ai_tone,
        "Здравствуйте! Спасибо за сообщение, скоро отвечу.",
        payload.text,
    )
    return AiPreviewOut(answer=answer, used_today=await ai.used_today(redis, owner.id))
