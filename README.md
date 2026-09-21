# Автопилот

Автоответчик и рассылки для Telegram: Gatekeeper Bot, Mini App, Backend API,
Userbot Worker. Статистика и админ-функции доступны прямо в Mini App — только
для Telegram `user_id` из `ADMIN_TELEGRAM_IDS`, без отдельного логина.
Архитектура, правила и инварианты проекта — в [`AGENTS.md`](./AGENTS.md).

## Деплой на VPS (production)

Полный стек одной командой через Docker Compose — см. **[`DEPLOY.md`](./DEPLOY.md)**.

## Локальная разработка

```bash
cp .env.example .env  # заполнить BOT_TOKEN, API_ID/API_HASH, ENCRYPTION_KEY и т.д.,
                       # для локальной разработки поменять хосты в DATABASE_URL/REDIS_URL
                       # с postgres/redis на localhost

docker-compose up -d postgres redis  # поднимает только БД и Redis (порты на localhost)

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head

uvicorn backend.main:app --reload --port 8000
python -m bot.main
python -m workers.scheduler
```

Mini App (в отдельном терминале):

```bash
cd frontend && npm install && npm run dev       # http://localhost:5173
```

## Тесты и линт

```bash
pytest
ruff check .
ruff format --check .
mypy .

cd frontend && npm run lint && npm run build
```
