from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    bot_username: str

    api_id: int
    api_hash: str

    encryption_key: str

    database_url: str
    redis_url: str

    jwt_secret: str
    admin_jwt_secret: str
    admin_username: str
    admin_password_hash: str  # bcrypt hash, generate with passlib/bcrypt CLI

    log_level: str = "INFO"

    # Gatekeeper bot
    required_channels: str = ""  # comma-separated @usernames or -100... chat ids
    webapp_url: str = ""

    @property
    def required_channels_list(self) -> list[str]:
        return [c.strip() for c in self.required_channels.split(",") if c.strip()]


settings = Settings()
