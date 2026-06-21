from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.opportunities import router as opportunities_router
from app.config import settings
from app.database import SessionLocal, engine
from app.models import Base, Opportunity
from app.services.opportunity_service import generate_excel_export, publish_event
from campushire_events import EventPublisher, EventType
from campushire_common.logging import get_logger

logger = get_logger("opportunity-service")
scheduler = BackgroundScheduler()
publisher = EventPublisher(settings.rabbitmq_url)


def process_deadlines():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = db.query(Opportunity).filter(
            Opportunity.deadline.isnot(None),
            Opportunity.deadline <= now,
            Opportunity.status == "published",
        ).all()
        for opp in due:
            generate_excel_export(db, opp.id)
            opp.status = "closed"
            db.commit()
            logger.info("Closed opportunity %s after deadline", opp.id)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await publisher.connect()
    scheduler.add_job(process_deadlines, "interval", minutes=1, id="deadline_checker")
    scheduler.start()
    logger.info("Opportunity service started")
    yield
    scheduler.shutdown()
    await publisher.close()


app = FastAPI(title="CampusHire Opportunity Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(opportunities_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "opportunity-service"}


@app.get("/api/v1/files/{folder}/{filename}")
def serve_local_file(folder: str, filename: str):
    if settings.storage_backend != "local":
        return {"detail": "Not available"}
    path = Path(settings.local_storage_path) / folder / filename
    if not path.exists():
        return {"detail": "Not found"}
    return FileResponse(path)
