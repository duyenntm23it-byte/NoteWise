import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import current_user_router, router as auth_router
from app.api.analytics import router as analytics_router
from app.api.documents import router as documents_router
from app.api.learning import router as learning_router
from app.api.quizzes import router as quizzes_router
from app.core.errors import ApiError, api_error_handler, validation_error_handler
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.documents import process_next_job
from app.services.learning import process_embedding_backfill

logger = logging.getLogger(__name__)


def _process_one_document_job() -> bool:
    with SessionLocal() as db:
        if process_next_job(db):
            return True
        return process_embedding_backfill(db) > 0


async def _document_worker_loop() -> None:
    while True:
        try:
            processed_job = await asyncio.to_thread(_process_one_document_job)
        except Exception:
            logger.exception("document_worker_iteration_failed")
            processed_job = False
        if not processed_job:
            await asyncio.sleep(settings.document_worker_poll_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    worker_task: asyncio.Task[None] | None = None
    if not getattr(app.state, "disable_document_worker", False):
        worker_task = asyncio.create_task(_document_worker_loop())
    try:
        yield
    finally:
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="NoteWise API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(current_user_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(learning_router, prefix="/api/v1")
app.include_router(quizzes_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
