from pydantic import BaseModel, Field

from backend.schemas.autoresponder import MAX_TEXT_LENGTH


class TemplateIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class TemplateOut(BaseModel):
    id: str  # "builtin:<slug>" or the numeric id of a saved template
    category: str
    title: str
    text: str
    builtin: bool
