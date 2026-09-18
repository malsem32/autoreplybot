from pyrogram import Client

from backend.core.config import settings
from backend.core.security import decrypt_session


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
        )
        await client.start()
        self._clients[account_id] = client
        return client

    def get(self, account_id: int) -> Client | None:
        return self._clients.get(account_id)

    async def stop(self, account_id: int) -> None:
        client = self._clients.pop(account_id, None)
        if client is not None:
            await client.stop()

    async def stop_all(self) -> None:
        for account_id in list(self._clients):
            await self.stop(account_id)


client_manager = ClientManager()
