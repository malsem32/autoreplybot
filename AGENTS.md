# AGENTS.md

## 1. Обзор проекта

Система автоматизации в Telegram, состоящая из пяти компонентов:

1. **Gatekeeper Bot (Bot API)** — входная точка: проверка подписки пользователя на обязательные каналы/чаты, запуск Mini App.
2. **Telegram Mini App (Frontend)** — веб-интерфейс для авторизации аккаунтов, настройки автоответчика и рассылок.
3. **Backend API** — обработка запросов от Mini App, валидация `initData`, управление зашифрованными MTProto-сессиями.
4. **Userbot Worker (MTProto Engine)** — клиентские инстансы (Pyrogram/Telethon), слушающие личные сообщения (автоответ) и отправляющие рассылки.
5. **Task Scheduler** — планировщик периодических и отложенных задач (APScheduler / ARQ).

## 2. Стек технологий

- **Язык:** Python 3.11+
- **Bot API:** `aiogram 3.x`
- **MTProto:** `Pyrogram` (или `hydrogram`) / `Telethon`
- **Backend:** `FastAPI`, `Pydantic v2`, `Uvicorn`
- **Frontend:** React / Vite, Tailwind CSS, `@twa-dev/sdk`
- **БД:** PostgreSQL, SQLAlchemy (async) + Alembic
- **Очереди/кэш:** Redis, `APScheduler` / `ARQ`
- **Криптография:** `cryptography` (Fernet) для строк сессий в БД

## 3. Структура репозитория

```text
├── bot/                  # Gatekeeper Bot (aiogram 3)
│   ├── handlers/         # /start, проверка подписки
│   ├── middlewares/      # Проверка членства в чатах
│   └── keyboards/        # Кнопки с WebAppInfo
├── backend/              # FastAPI сервис
│   ├── api/              # auth, autoresponder, broadcasts, dialogs
│   ├── core/             # конфиг, безопасность (Fernet, JWT, initData hash)
│   ├── models/           # SQLAlchemy модели
│   ├── schemas/          # Pydantic схемы
│   └── services/         # бизнес-логика
├── workers/              # Userbot движок и планировщик
│   ├── client_manager.py # пул запущенных Pyrogram клиентов
│   ├── responder.py      # обработчики on_message для автоответа
│   ├── broadcaster.py    # логика отправки сообщений
│   └── scheduler.py      # периодические задачи
├── frontend/             # Telegram Mini App (React + Vite)
│   └── src/{api,components,pages}/
├── docker-compose.yml
├── .env.example
└── README.md
```

Точную схему БД смотреть в `backend/models/` и актуальных Alembic-миграциях, команды запуска — в `README.md`. Этот файл не дублирует их специально, чтобы не расходиться с кодом.

## 4. Правила и инварианты (обязательны к соблюдению)

### 4.1. Безопасность MTProto-сессий

- Запрещено хранить `StringSession` в открытом виде — только зашифрованной `ENCRYPTION_KEY` (Fernet) перед записью в БД.
- Поток авторизации: `send_code(phone)` → `phone_code_hash` → `sign_in(phone, phone_code_hash, code)` → при 2FA `check_password(password)` → сохранение session string → очистка временных токенов авторизации.
- Никогда не логировать: номера телефонов, коды подтверждения, пароли 2FA, session string, `api_id`/`api_hash`.

### 4.2. Валидация Mini App

- Все запросы к `/api/*` передают `Authorization: tma <initData>`.
- Бэкенд обязан валидировать подпись `initData` через HMAC-SHA256 с токеном бота на каждом защищённом эндпоинте. Невалидные запросы → `401`.

### 4.3. Антибан / ограничения Telegram

- Между отправками сообщений в разные чаты — случайная задержка 20–45 секунд.
- Все MTProto-вызовы оборачивать в обработку `FloodWait`: при исключении — sleep `e.value + 5` сек или откладывание задачи, без ретрая "в лоб".
- Рассыльщик поддерживает spintax `{Вариант1|Вариант2|Вариант3}`.
- Автоответчик: игнорировать `message.from_user.is_bot`, cooldown не менее 1–2 часов на диалог (`user_id`).

### 4.4. Секреты и конфигурация

- Не коммитить `.env`, реальные `api_id`/`api_hash`, токены ботов, `ENCRYPTION_KEY`. Только `.env.example` с плейсхолдерами.
- Секреты читаются из окружения (`backend/core/config.py`), не хардкодятся.

## 5. Локальный запуск

```bash
# Инфраструктура
docker-compose up -d postgres redis

# Окружение
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Миграции
alembic upgrade head

# Сервисы (в отдельных терминалах)
uvicorn backend.main:app --reload --port 8000
python -m bot.main
python -m workers.scheduler
```

## 6. Чек-лист перед коммитом

- [ ] Не логируются чувствительные данные (телефоны, коды, 2FA-пароли, session string).
- [ ] Асинхронный жизненный цикл Pyrogram-клиента (запуск/остановка/дисконнект) обработан корректно.
- [ ] Новые эндпоинты `/api/*` закрыты middleware-проверкой `initData`.
- [ ] Новые методы отправки учитывают `FloodWait`, задержки и cooldown (см. 4.3).
- [ ] В диффе нет секретов (`.env`, ключи, токены).
