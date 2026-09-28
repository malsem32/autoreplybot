from datetime import datetime

from pydantic import BaseModel, Field, computed_field, field_validator

from backend.core.uploads import photo_url
from backend.schemas.autoresponder import MAX_PHOTOS, MAX_TEXT_LENGTH
from backend.services.ai import MAX_KNOWLEDGE_CHARS, TONES
from backend.services.schedule import valid_timezone
from backend.services.snippets import SHORTCUT_RE, normalize_shortcut

# --- Vacation mode ---------------------------------------------------------------


class AwayOut(BaseModel):
    active: bool
    until: datetime | None
    text: str
    preview: str  # the text as clients will see it, with {дата} filled in


class AwayIn(BaseModel):
    until: datetime
    text: str = Field(min_length=1, max_length=1000)
    timezone: str = "Europe/Moscow"  # IANA name; the {дата} placeholder uses it

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        if not valid_timezone(value):
            raise ValueError("неизвестный часовой пояс")
        return value


# --- Quick phrases ---------------------------------------------------------------


class _ShortcutValidator(BaseModel):
    @field_validator("shortcut", check_fields=False)
    @classmethod
    def _check_shortcut(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = normalize_shortcut(value)
        if not SHORTCUT_RE.match(value):
            raise ValueError("только буквы, цифры и _, до 32 символов, без пробелов")
        return value


class SnippetIn(_ShortcutValidator):
    shortcut: str
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    photos: list[str] = Field(default_factory=list, max_length=MAX_PHOTOS)


class SnippetUpdate(_ShortcutValidator):
    shortcut: str | None = None
    text: str | None = Field(min_length=1, max_length=MAX_TEXT_LENGTH, default=None)
    photos: list[str] | None = Field(max_length=MAX_PHOTOS, default=None)


class SnippetOut(BaseModel):
    id: int
    shortcut: str
    text: str
    photo_paths: list[str] = Field(exclude=True, default_factory=list)

    class Config:
        from_attributes = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_urls(self) -> list[str]:
        return [photo_url(p) for p in self.photo_paths or []]


class SnippetListOut(BaseModel):
    snippets: list[SnippetOut]
    limit: int | None  # None = unlimited (Pro)


# --- AI ------------------------------------------------------------------------


class AiSettingsOut(BaseModel):
    available: bool  # the server has an AI provider configured
    knowledge: str
    tone: str
    daily_limit: int
    used_today: int


class AiSettingsIn(BaseModel):
    knowledge: str = Field(max_length=MAX_KNOWLEDGE_CHARS)
    tone: str = Field(pattern="^(" + "|".join(TONES) + ")$")


class AiPreviewIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class AiPreviewOut(BaseModel):
    answer: str | None  # None: the AI didn't answer, the rule text would be sent
    used_today: int
