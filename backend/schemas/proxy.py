from datetime import datetime

from pydantic import BaseModel, Field


class ProxyIn(BaseModel):
    protocol: str = Field(pattern="^(socks5|http)$", default="socks5")
    host: str
    port: int = Field(ge=1, le=65535)
    username: str | None = None
    password: str | None = None
    is_active: bool = True


class ProxyUpdate(BaseModel):
    protocol: str | None = Field(pattern="^(socks5|http)$", default=None)
    host: str | None = None
    port: int | None = Field(ge=1, le=65535, default=None)
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None


class ProxyOut(BaseModel):
    id: int
    protocol: str
    host: str
    port: int
    username: str | None
    is_active: bool
    last_checked_at: datetime | None
    last_status: str | None
    last_latency_ms: int | None

    class Config:
        from_attributes = True
