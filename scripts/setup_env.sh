#!/bin/sh
# Generates .env from .env.example and fills in the secret that can be
# generated automatically (ENCRYPTION_KEY). Fields that only a human can
# know (BOT_TOKEN, API_ID/API_HASH, domain, required channels, admin
# telegram ids) are left for manual editing.
set -e

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

set_var() {
    key="$1"
    value="$2"
    if grep -q "^${key}=" .env; then
        sed -i.bak "s|^${key}=.*|${key}=${value}|" .env && rm -f .env.bak
    else
        echo "${key}=${value}" >> .env
    fi
}

is_empty() {
    key="$1"
    current="$(grep "^${key}=" .env | cut -d= -f2-)"
    [ -z "$current" ]
}

PY="python3"

if is_empty ENCRYPTION_KEY; then
    KEY="$($PY -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
    set_var ENCRYPTION_KEY "$KEY"
    echo "Generated ENCRYPTION_KEY"
fi

echo
echo "Done. Still fill in manually (need info only you have):"
echo "  BOT_TOKEN, BOT_USERNAME, API_ID, API_HASH"
echo "  APP_DOMAIN, WEBAPP_URL"
echo "  REQUIRED_CHANNELS, ADMIN_TELEGRAM_IDS (your Telegram user_id from @userinfobot)"
echo
echo "Then run: docker compose up -d --build"
