# Автопилот

Автоответчик и рассылки для Telegram: Gatekeeper Bot, Mini App, Backend API,
Userbot Worker и Admin Panel. Архитектура, правила и инварианты проекта — в
[`AGENTS.md`](./AGENTS.md).

## Быстрый старт

```bash
cp .env.example .env  # заполнить BOT_TOKEN, API_ID/API_HASH, ENCRYPTION_KEY и т.д.

docker-compose up -d postgres redis

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head

uvicorn backend.main:app --reload --port 8000
python -m bot.main
python -m workers.scheduler
```

## Тесты и линт

```bash
pytest
ruff check .
ruff format --check .
mypy .
```
