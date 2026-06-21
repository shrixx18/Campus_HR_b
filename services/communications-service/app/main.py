import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.communications import router as communications_router
from app.config import settings
from app.database import engine
from app.models import Base
from app.services.communications_service import handle_domain_event
from campushire_events import EventConsumer, EventType
from campushire_common.logging import get_logger

logger = get_logger("communications-service")


async def run_consumer():
    consumer = EventConsumer(settings.rabbitmq_url)
    for event_type in [
        EventType.APPLICATION_SUBMITTED,
        EventType.APPLICATION_SHORTLISTED,
        EventType.APPLICATION_REJECTED,
        EventType.QUERY_RESPONDED,
        EventType.DRIVE_CREATED,
        EventType.DRIVE_UPDATED,
    ]:
        consumer.register(event_type, handle_domain_event)
    await consumer.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(run_consumer())
    logger.info("Communications service started")
    yield
    task.cancel()


app = FastAPI(title="CampusHire Communications Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(communications_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "communications-service"}
