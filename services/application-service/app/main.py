from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.applications import router as applications_router
from app.config import settings
from app.database import engine
from app.models import Base
from campushire_events import EventPublisher
from campushire_common.logging import get_logger

logger = get_logger("application-service")
publisher = EventPublisher(settings.rabbitmq_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await publisher.connect()
    app.state.publisher = publisher
    logger.info("Application service started")
    yield
    await publisher.close()


app = FastAPI(title="CampusHire Application Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(applications_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "application-service"}


@app.get("/api/v1/files/{folder}/{filename}")
def serve_local_file(folder: str, filename: str):
    if settings.storage_backend != "local":
        return {"detail": "Not available"}
    path = Path(settings.local_storage_path) / folder / filename
    if not path.exists():
        return {"detail": "Not found"}
    return FileResponse(path)
