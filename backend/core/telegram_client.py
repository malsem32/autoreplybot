"""How our MTProto clients introduce themselves to Telegram.

Telegram shows these values on the account's "Devices" screen and in the
"new login" notice, and refreshes them every time a client connects. The
login flow (backend/api/auth.py) and the worker (workers/client_manager.py)
use the same session, so they must send the same identity — otherwise the
one session shows up as "Автопилот Web" at login and then as
"Pyrogram / CPython" once the worker connects, which looks like two
different logins and can look suspicious to Telegram as well.
"""

from typing import TypedDict


class ClientIdentity(TypedDict):
    app_version: str
    device_model: str
    system_version: str
    lang_code: str
    system_lang_code: str


CLIENT_IDENTITY: ClientIdentity = {
    "app_version": "1.0",
    "device_model": "Автопилот",
    "system_version": "Сервер",
    "lang_code": "ru",
    "system_lang_code": "ru",
}
