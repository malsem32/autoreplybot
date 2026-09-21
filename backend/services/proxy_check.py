import asyncio
import time

from backend.models.proxy import Proxy

CHECK_TIMEOUT_SECONDS = 5


async def check_proxy(proxy: Proxy) -> tuple[str, int | None]:
    """TCP-connect liveness check against the proxy's own host:port.

    This confirms the proxy endpoint is reachable, not that a full
    SOCKS5/HTTP handshake and outbound request through it succeeds — a
    lightweight signal, not a guarantee.
    """
    start = time.monotonic()
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(proxy.host, proxy.port), timeout=CHECK_TIMEOUT_SECONDS
        )
        writer.close()
        await writer.wait_closed()
        latency_ms = int((time.monotonic() - start) * 1000)
        return "alive", latency_ms
    except (OSError, TimeoutError, asyncio.TimeoutError):
        return "dead", None
