#!/usr/bin/env bash
# Replaces an old "autoreply" deployment on a VPS with Автопилот, reusing its
# settings (bot token, domain, API keys...). Other containers are not touched.
#
#   curl -fsSL https://raw.githubusercontent.com/malsem32/autoreplybot/claude/jolly-heisenberg-un9avi/scripts/redeploy_server.sh -o redeploy.sh
#   DRY_RUN=1 bash redeploy.sh    # only shows what it found and would do
#   bash redeploy.sh              # does it (asks for confirmation first)
#
# Env overrides: OLD_NAME (default autoreply), TARGET (/opt/autopilot),
# REPO_URL, BRANCH, KEEP_DATA=yes|no (reuse the old Postgres volume when the
# old stack was this same project; auto-detected otherwise).
set -euo pipefail

OLD_NAME="${OLD_NAME:-autoreply}"
TARGET="${TARGET:-/opt/autopilot}"
REPO_URL="${REPO_URL:-https://github.com/malsem32/autoreplybot.git}"
BRANCH="${BRANCH:-claude/jolly-heisenberg-un9avi}"
DRY_RUN="${DRY_RUN:-0}"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die() { printf '\n\033[31mОшибка: %s\033[0m\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || die "docker не установлен"
docker compose version >/dev/null 2>&1 || die "нужен docker compose v2 (docker compose version)"
command -v git >/dev/null || die "git не установлен (apt install -y git)"

# --- 1. Find the old deployment ------------------------------------------------
say "1. Ищу старые контейнеры с «${OLD_NAME}» в имени или compose-проекте"
mapfile -t OLD_CONTAINERS < <(
    docker ps -a --format '{{.Names}}\t{{.Label "com.docker.compose.project"}}' |
        awk -F'\t' -v n="$OLD_NAME" 'tolower($1) ~ tolower(n) || tolower($2) ~ tolower(n) {print $1}'
)
if [ "${#OLD_CONTAINERS[@]}" -eq 0 ]; then
    echo "Не найдено. Будет чистая установка."
else
    printf '  • %s\n' "${OLD_CONTAINERS[@]}"
fi

OLD_PROJECT=""
OLD_DIR=""
if [ "${#OLD_CONTAINERS[@]}" -gt 0 ]; then
    OLD_PROJECT="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "${OLD_CONTAINERS[0]}" 2>/dev/null || true)"
    OLD_DIR="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' "${OLD_CONTAINERS[0]}" 2>/dev/null || true)"
    echo "  compose-проект: ${OLD_PROJECT:-нет}; папка: ${OLD_DIR:-неизвестно}"
fi

# --- 2. Collect settings --------------------------------------------------------
say "2. Собираю настройки"
ENV_TMP="$(mktemp)"
trap 'rm -f "$ENV_TMP"' EXIT
if [ -n "$OLD_DIR" ] && [ -f "$OLD_DIR/.env" ]; then
    cp "$OLD_DIR/.env" "$ENV_TMP"
    echo "  взят $OLD_DIR/.env"
elif [ -f "$TARGET/.env" ]; then
    cp "$TARGET/.env" "$ENV_TMP"
    echo "  взят $TARGET/.env"
elif [ "${#OLD_CONTAINERS[@]}" -gt 0 ]; then
    # No .env file: take the variables straight from the old containers.
    for c in "${OLD_CONTAINERS[@]}"; do
        docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$c"
    done | grep -E '^(BOT_TOKEN|BOT_USERNAME|API_ID|API_HASH|ENCRYPTION_KEY|APP_DOMAIN|WEBAPP_URL|REQUIRED_CHANNELS|ADMIN_TELEGRAM_IDS|AI_[A-Z_]+)=' |
        sort -u -t= -k1,1 >"$ENV_TMP" || true
    echo "  .env не найден — переменные взяты из окружения контейнеров"
fi

# Show which keys were found, never their values.
for key in BOT_TOKEN BOT_USERNAME API_ID API_HASH ENCRYPTION_KEY APP_DOMAIN WEBAPP_URL ADMIN_TELEGRAM_IDS; do
    if grep -qE "^${key}=.+" "$ENV_TMP"; then echo "  ✓ $key"; else echo "  ✗ $key — не найден"; fi
done

# --- 3. Ports 80/443 -------------------------------------------------------------
say "3. Проверяю, свободны ли порты 80/443 (нужны Caddy для HTTPS)"
BUSY="$(docker ps --format '{{.Names}}\t{{.Ports}}' | grep -E '0\.0\.0\.0:(80|443)->|:::(80|443)->' || true)"
CONFLICT=""
while IFS=$'\t' read -r name ports; do
    [ -z "$name" ] && continue
    if ! printf '%s\n' "${OLD_CONTAINERS[@]:-}" | grep -qx "$name"; then
        CONFLICT="${CONFLICT}  • ${name} (${ports})\n"
    fi
done <<<"$BUSY"
if [ -n "$CONFLICT" ]; then
    printf '  Порты заняты другими контейнерами (их не трогаю):\n%b' "$CONFLICT"
    die "освободите 80/443 или настройте существующий прокси на этот стек вручную — см. DEPLOY.md"
fi
echo "  свободны (или заняты только старым autoreply)"

# --- 4. Data --------------------------------------------------------------------
PROJECT_NAME="autopilot"
if [ -z "${KEEP_DATA:-}" ]; then
    KEEP_DATA="no"
    if [ -n "$OLD_PROJECT" ] && docker volume inspect "${OLD_PROJECT}_postgres_data" >/dev/null 2>&1 &&
        docker ps -a --format '{{.Label "com.docker.compose.service"}}' --filter "label=com.docker.compose.project=${OLD_PROJECT}" | grep -qx worker; then
        KEEP_DATA="yes" # same project layout: accounts and rules survive, migrations upgrade the DB
    fi
fi
if [ "$KEEP_DATA" = "yes" ]; then
    PROJECT_NAME="$OLD_PROJECT"
    echo "  Данные старой установки (том ${OLD_PROJECT}_postgres_data) будут сохранены и обновлены миграциями."
else
    echo "  Будет новая база. Старые тома не удаляются — их можно удалить вручную позже."
fi

say "План"
echo "  • остановить и удалить: ${OLD_CONTAINERS[*]:-ничего}"
echo "  • код: ${REPO_URL} (${BRANCH}) → ${TARGET}"
echo "  • запустить compose-проект «${PROJECT_NAME}»"
if [ "$DRY_RUN" = "1" ]; then
    say "DRY_RUN=1 — ничего не изменено."
    exit 0
fi
read -r -p "Продолжить? Напишите yes: " answer
[ "$answer" = "yes" ] || die "отменено"

# --- 5. Remove the old deployment ------------------------------------------------
if [ "${#OLD_CONTAINERS[@]}" -gt 0 ]; then
    say "5. Удаляю старые контейнеры (тома остаются)"
    if [ -n "$OLD_PROJECT" ] && [ -n "$OLD_DIR" ] && [ -d "$OLD_DIR" ]; then
        (cd "$OLD_DIR" && docker compose -p "$OLD_PROJECT" down --remove-orphans) || true
    fi
    for c in "${OLD_CONTAINERS[@]}"; do docker rm -f "$c" >/dev/null 2>&1 || true; done
fi

# --- 6. Code + settings ----------------------------------------------------------
say "6. Скачиваю код"
if [ -d "$TARGET/.git" ]; then
    git -C "$TARGET" fetch origin "$BRANCH"
    git -C "$TARGET" checkout -B "$BRANCH" "origin/$BRANCH"
else
    mkdir -p "$(dirname "$TARGET")"
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET"
fi
cd "$TARGET"
[ -s "$ENV_TMP" ] && cp "$ENV_TMP" .env
[ -f .env ] || cp .env.example .env
# Inside compose the services are reached by name.
sed -i -E 's|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://autopilot:autopilot@postgres:5432/autopilot|; s|^REDIS_URL=.*|REDIS_URL=redis://redis:6379/0|' .env
grep -q '^DATABASE_URL=' .env || echo 'DATABASE_URL=postgresql+asyncpg://autopilot:autopilot@postgres:5432/autopilot' >>.env
grep -q '^REDIS_URL=' .env || echo 'REDIS_URL=redis://redis:6379/0' >>.env
# Missing keys from the current template are appended empty; ENCRYPTION_KEY is
# generated only if absent (an existing key must stay — it decrypts sessions).
while IFS= read -r line; do
    key="${line%%=*}"
    case "$key" in '' | \#*) continue ;; esac
    grep -q "^${key}=" .env || echo "$line" >>.env
done <.env.example
# The Mini App URL follows the domain unless set explicitly.
DOMAIN="$(grep '^APP_DOMAIN=' .env | cut -d= -f2-)"
if [ -n "$DOMAIN" ] && ! grep -qE '^WEBAPP_URL=.+' .env; then
    sed -i "s|^WEBAPP_URL=.*|WEBAPP_URL=https://${DOMAIN}|" .env
fi
sh scripts/setup_env.sh >/dev/null
chmod 600 .env

for key in BOT_TOKEN BOT_USERNAME API_ID API_HASH APP_DOMAIN; do
    grep -qE "^${key}=.+" .env || die "в $TARGET/.env не заполнен $key — впишите и запустите: cd $TARGET && docker compose -p $PROJECT_NAME up -d --build"
done

# --- 7. Start --------------------------------------------------------------------
say "7. Собираю и запускаю (первый раз — несколько минут)"
docker compose -p "$PROJECT_NAME" up -d --build
sleep 5
docker compose -p "$PROJECT_NAME" ps
say "Готово: https://${DOMAIN}"
echo "Логи: cd $TARGET && docker compose -p $PROJECT_NAME logs -f --tail=100 backend bot worker"
echo "В @BotFather у кнопки Mini App должен быть адрес https://${DOMAIN}"
