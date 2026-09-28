import logging

from pyrogram import Client

from backend.core.config import settings
from backend.core.security import decrypt_session
from backend.core.telegram_client import CLIENT_IDENTITY

logger = logging.getLogger(__name__)


class ClientManager:
    """Holds one running Pyrogram client per TelegramAccount.id.

    Per AGENTS.md 4.5: clients of different accounts never share state,
    handlers, or task queues. Each entry here is fully independent.
    """

    def __init__(self) -> None:
        self._clients: dict[int, Client] = {}

    async def start(self, account_id: int, encrypted_session: str) -> Client:
        if account_id in self._clients:
            return self._clients[account_id]

        client = Client(
            name=f"account_{account_id}",
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            session_string=decrypt_session(encrypted_session),
            in_memory=True,
            # Same identity as at login: one session, one name on "Devices".
            **CLIENT_IDENTITY,
        )
        await client.start()
        self._clients[account_id] = client
        return client

    def get(self, account_id: int) -> Client | None:
        return self._clients.get(account_id)

    def running_ids(self) -> set[int]:
        return set(self._clients)

    async def stop(self, account_id: int) -> None:
        client = self._clients.pop(account_id, None)
        if client is not None:
            try:
                await client.stop()
            except Exception:  # noqa: BLE001 - the client is dropped from the pool regardless
                logger.warning("failed to stop client for account %s cleanly", account_id)

    async def stop_all(self) -> None:
        for account_id in list(self._clients):
            await self.stop(account_id)


client_manager = ClientManager()
