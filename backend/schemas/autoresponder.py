from pydantic import BaseModel, Field, computed_field

from backend.core.uploads import photo_url

# Telegram's own limits: 4096 chars per message, 10 items per album.
MAX_TEXT_LENGTH = 4096
MAX_PHOTOS = 10


class AutoresponderRuleIn(BaseModel):
    is_enabled: bool = True
    trigger_type: str = Field(pattern="^(all|keywords)$", default="all")
    keywords: list[str] = Field(default_factory=list)
    response_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    # Upload refs (path / URL / filename from POST /api/uploads/photo).
    photos: list[str] = Field(default_factory=list, max_length=MAX_PHOTOS)
    cooldown_seconds: int = Field(ge=3600, default=3600)  # min 1h, see AGENTS.md 4.3


class AutoresponderRuleUpdate(BaseModel):
    is_enabled: bool | None = None
    trigger_type: str | None = Field(pattern="^(all|keywords)$", default=None)
    keywords: list[str] | None = None
    response_text: str | None = Field(min_length=1, max_length=MAX_TEXT_LENGTH, default=None)
    # Replaces the whole photo list when given; [] removes all photos.
    photos: list[str] | None = Field(max_length=MAX_PHOTOS, default=None)
    cooldown_seconds: int | None = Field(ge=3600, default=None)


class AutoresponderRuleOut(BaseModel):
    id: int
    account_id: int
    is_enabled: bool
    trigger_type: str
    keywords: list[str]
    response_text: str
    cooldown_seconds: int
    photo_paths: list[str] = Field(exclude=True, default_factory=list)

    class Config:
        from_attributes = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_urls(self) -> list[str]:
        return [photo_url(p) for p in self.photo_paths or []]
