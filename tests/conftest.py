import os

os.environ.setdefault("BOT_TOKEN", "123456:test-token")
os.environ.setdefault("BOT_USERNAME", "test_bot")
os.environ.setdefault("API_ID", "1")
os.environ.setdefault("API_HASH", "test-hash")
os.environ.setdefault("ENCRYPTION_KEY", "5c1MlveGejx_zjt42rCPhtKNiZamVKlLmk7BnNy24Yc=")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ADMIN_JWT_SECRET", "test-admin-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault(
    "ADMIN_PASSWORD_HASH", "$2b$12$abcdefghijklmnopqrstuuZWm0000000000000000000000000000"
)
