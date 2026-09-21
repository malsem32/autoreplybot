from pydantic import BaseModel, Field, computed_field


def _photo_url(path: str | None) -> str | None:
    if not path:
        return None
    filename = path.rsplit("/", 1)[-1]
    return f"/api/uploads/{filename}"


class AutoresponderRuleIn(BaseModel):
    is_enabled: bool = True
    trigger_type: str = Field(pattern="^(all|keywords)$", default="all")
    keywords: list[str] = Field(default_factory=list)
    response_text: str
    photo_path: str | None = None
    cooldown_seconds: int = Field(ge=3600, default=3600)  # min 1h, see AGENTS.md 4.3


class AutoresponderRuleUpdate(BaseModel):
    is_enabled: bool | None = None
    trigger_type: str | None = Field(pattern="^(all|keywords)$", default=None)
    keywords: list[str] | None = None
    response_text: str | None = None
    photo_path: str | None = None
    remove_photo: bool = False
    cooldown_seconds: int | None = Field(ge=3600, default=None)


class AutoresponderRuleOut(BaseModel):
    id: int
    account_id: int
    is_enabled: bool
    trigger_type: str
    keywords: list[str]
    response_text: str
    cooldown_seconds: int
    photo_path: str | None = Field(exclude=True, default=None)

    class Config:
        from_attributes = True

    @computed_field
    @property
    def photo_url(self) -> str | None:
        return _photo_url(self.photo_path)
