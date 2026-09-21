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

    log_level: str = "INFO"

    # Gatekeeper bot
    required_channels: str = ""  # comma-separated @usernames or -100... chat ids
    webapp_url: str = ""

    # Telegram user_ids allowed to see /api/admin/* inside the Mini App
    admin_telegram_ids: str = ""

    @property
    def required_channels_list(self) -> list[str]:
        return [c.strip() for c in self.required_channels.split(",") if c.strip()]

    @property
    def admin_telegram_ids_list(self) -> list[int]:
        return [int(i.strip()) for i in self.admin_telegram_ids.split(",") if i.strip()]


settings = Settings()
