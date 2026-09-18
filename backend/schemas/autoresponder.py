from pydantic import BaseModel, Field


class AutoresponderRuleIn(BaseModel):
    is_enabled: bool = True
    trigger_type: str = Field(pattern="^(all|keywords)$", default="all")
    keywords: list[str] = Field(default_factory=list)
    response_text: str
    cooldown_seconds: int = Field(ge=3600, default=3600)  # min 1h, see AGENTS.md 4.3


class AutoresponderRuleOut(AutoresponderRuleIn):
    id: int
    account_id: int

    class Config:
        from_attributes = True
