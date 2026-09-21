# Деплой на VPS

Полный стек (Postgres, Redis, backend, Gatekeeper Bot, воркер рассылок/автоответчика,
Mini App, Caddy с автоматическим HTTPS) поднимается одной командой через Docker Compose.
Статистика и админ-функции доступны прямо внутри Mini App — только для Telegram
`user_id`, перечисленных в `ADMIN_TELEGRAM_IDS`, отдельного логина/пароля нет.

## Требования

- VPS с Docker и Docker Compose (`docker compose version` должен работать).
- DNS A-запись, указывающая на IP сервера: `app.your-domain.example` (Mini App).
- Открытые порты 80 и 443 (для Caddy и Let's Encrypt).
- Бот, зарегистрированный в @BotFather (`BOT_TOKEN`), и `API_ID`/`API_HASH` с
  [my.telegram.org](https://my.telegram.org).
- Ваш Telegram `user_id` (не username) — узнать у @userinfobot.

## Шаги

1. Склонировать репозиторий и перейти в него:

   ```bash
   git clone <repo-url> autoreplybot
   cd autoreplybot
   ```

2. Сгенерировать `.env` с автоматическими секретами:

   ```bash
   ./scripts/setup_env.sh
   ```

   Скрипт создаст `.env` из `.env.example` и сам сгенерирует `ENCRYPTION_KEY`.

3. Открыть `.env` и заполнить то, что знаете только вы:

   - `BOT_TOKEN`, `BOT_USERNAME`, `API_ID`, `API_HASH` — из BotFather / my.telegram.org.
   - `APP_DOMAIN` — домен из шага с DNS, `WEBAPP_URL` — `https://` + `APP_DOMAIN`.
   - `REQUIRED_CHANNELS` — через запятую `@username` каналов, обязательных для подписки
     (можно оставить пустым, если проверка подписки не нужна).
   - `ADMIN_TELEGRAM_IDS` — ваш Telegram `user_id` (через запятую, если админов
     несколько) — только эти аккаунты увидят раздел статистики внутри Mini App.
   - `DATABASE_URL`/`REDIS_URL` можно оставить как в `.env.example` — они указывают
     на сервисы `postgres`/`redis` внутри docker-сети.

4. Собрать и запустить весь стек:

   ```bash
   docker compose up -d --build
   ```

   При первом запуске сервис `backend` сам применит миграции Alembic (`RUN_MIGRATIONS=true`).

5. Проверить статус:

   ```bash
   docker compose ps
   docker compose logs -f backend bot worker caddy
   ```

   Caddy получит сертификат Let's Encrypt для `APP_DOMAIN` автоматически — на это
   может уйти до пары минут при первом запуске.

6. В @BotFather:
   - `/setuserpic` → загрузить `assets/branding/avatar_512.png`;
   - `/setabouttext` и `/setdescription` → тексты из `AGENTS.md` (раздел 0).

7. Открыть бота в Telegram, нажать `/start` → «Открыть Автопилот», подключить
   свой Telegram-аккаунт. Если ваш `user_id` указан в `ADMIN_TELEGRAM_IDS`,
   в Mini App появится вкладка со статистикой.

## Обновление после изменений в коде

```bash
git pull
docker compose up -d --build
```

Пересоберутся только изменившиеся образы; Postgres/Redis данные сохраняются в
именованных volume'ах (`postgres_data`, `redis_data`) и не теряются между деплоями.

## Резервное копирование БД

```bash
docker compose exec postgres pg_dump -U autopilot autopilot > backup.sql
```

## Локальная разработка без Docker

См. основной [`README.md`](./README.md) — `docker-compose up -d postgres redis`
поднимает только БД и Redis, остальное запускается напрямую (`uvicorn`,
`python -m bot.main`, `python -m workers.scheduler`, `npm run dev` во `frontend/`).
