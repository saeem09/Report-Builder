from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .reports import register_exception_handlers, router as reports_router

# The Vite dev server's default port. Both spellings of loopback are listed
# because a browser treats http://localhost:5173 and http://127.0.0.1:5173 as
# different origins and a developer may type either one.
#
# This is a local development policy only. There is no deployment target for
# this MVP; a real origin policy for a hosted environment is out of scope and
# must be revisited before this application is deployed anywhere.
DEV_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")

# Listed explicitly rather than "*" so that widening the surface is a visible
# edit rather than an accident.
ALLOWED_METHODS = ("GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS")

# The only request header the frontend sets by hand. Multipart uploads let the
# browser set Content-Type itself (it has to, to add the boundary), and
# Starlette always permits the CORS-safelisted request headers.
ALLOWED_HEADERS = ("Content-Type",)

# Without this, JavaScript cannot read the filename the PDF export sends back,
# because Content-Disposition is not a CORS-safelisted response header.
EXPOSED_HEADERS = ("Content-Disposition",)


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

# allow_credentials stays False: this MVP has no accounts, no cookies, and no
# authorization header, so there is nothing for a cross-origin request to
# carry. Keeping it False is also what makes a fixed origin list sufficient.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(DEV_ORIGINS),
    allow_credentials=False,
    allow_methods=list(ALLOWED_METHODS),
    allow_headers=list(ALLOWED_HEADERS),
    expose_headers=list(EXPOSED_HEADERS),
)

register_exception_handlers(app)
app.include_router(reports_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
