from fastapi import FastAPI

from backend.admin.auth import router as admin_auth_router
from backend.admin.stats import router as admin_stats_router
from backend.api.auth import router as auth_router
from backend.api.autoresponder import router as autoresponder_router
from backend.api.broadcasts import router as broadcasts_router
from backend.api.dialogs import router as dialogs_router
from backend.core.logging import configure_logging

configure_logging()

app = FastAPI(title="Autopilot Backend")

app.include_router(auth_router)
app.include_router(autoresponder_router)
app.include_router(broadcasts_router)
app.include_router(dialogs_router)
app.include_router(admin_auth_router)
app.include_router(admin_stats_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
