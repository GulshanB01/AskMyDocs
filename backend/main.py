from datetime import datetime

from fastapi import FastAPI

from backend.routes.admin import router as admin_router
from backend.routes.auth import router as auth_router
from backend.routes.chat import router as chat_router
from backend.routes.documents import router as documents_router
from backend.routes.jobs import router as jobs_router
from backend.routes.tags import router as tags_router


app = FastAPI(
    title="AskMyDocs API",
    description="Backend API for the AskMyDocs document intelligence system.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(jobs_router)
app.include_router(chat_router)
app.include_router(tags_router)
app.include_router(admin_router)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "askmydocs-api",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
