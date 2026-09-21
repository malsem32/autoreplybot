from fastapi import FastAPI

from backend.api.admin import router as admin_router
from backend.api.auth import router as auth_router
from backend.api.autoresponder import router as autoresponder_router
from backend.api.broadcasts import router as broadcasts_router
from backend.api.dialogs import router as dialogs_router
from backend.api.uploads import router as uploads_router
from backend.core.logging import configure_logging

configure_logging()

app = FastAPI(title="Autopilot Backend")

app.include_router(auth_router)
app.include_router(autoresponder_router)
app.include_router(broadcasts_router)
app.include_router(dialogs_router)
app.include_router(uploads_router)
app.include_router(admin_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
