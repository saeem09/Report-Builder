from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from .db import init_db
from .reports import register_exception_handlers, router as reports_router


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Create the database file and its tables before the first request.

    init_db applies schema.sql, whose statements are all CREATE ... IF NOT
    EXISTS, so running this on every startup is idempotent. This is the
    deferred wiring flagged in the Phase 1 review: until now nothing called
    init_db, so the API had no database to talk to.
    """
    init_db()
    yield


app = FastAPI(title="Progress Report API", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(reports_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
