from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user
from backend.db.session import get_db
from backend.models.template import MessageTemplate
from backend.models.user import User
from backend.schemas.template import TemplateIn, TemplateOut
from backend.services import pro
from backend.services.templates import BUILTIN_TEMPLATES

router = APIRouter(prefix="/api/templates", tags=["templates"])

MAX_TEMPLATES_PER_USER = 100


def _saved_out(t: MessageTemplate) -> TemplateOut:
    return TemplateOut(
        id=str(t.id), category="Мои шаблоны", title=t.title, text=t.text, builtin=False
    )


@router.get("", response_model=list[TemplateOut])
async def list_templates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TemplateOut]:
    """The user's saved templates first, then the built-in library."""
    saved = (
        await db.execute(
            select(MessageTemplate)
            .where(MessageTemplate.user_id == user.id)
            .order_by(MessageTemplate.id.desc())
        )
    ).scalars()
    builtin = [
        TemplateOut(
            id=f"builtin:{t['id']}",
            builtin=True,
            **{k: t[k] for k in ("category", "title", "text")},
        )
        for t in BUILTIN_TEMPLATES
    ]
    return [_saved_out(t) for t in saved] + builtin


@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(
    payload: TemplateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TemplateOut:
    if not pro.has_access(user):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Свои шаблоны доступны в Pro")
    count = await db.scalar(
        select(func.count()).select_from(MessageTemplate).where(MessageTemplate.user_id == user.id)
    )
    if (count or 0) >= MAX_TEMPLATES_PER_USER:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Можно сохранить до {MAX_TEMPLATES_PER_USER} шаблонов"
        )
    template = MessageTemplate(user_id=user.id, title=payload.title.strip(), text=payload.text)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return _saved_out(template)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    template = await db.scalar(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id, MessageTemplate.user_id == user.id
        )
    )
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Шаблон не найден")
    await db.delete(template)
    await db.commit()
