"""The progress report feature: CRUD, uploads, AI generation, and PDF export.

app.main imports exactly two names from here: router and
register_exception_handlers.
"""

from fastapi import APIRouter

from .exception_handlers import register_exception_handlers
from .pipeline_routes import router as pipeline_router
from .routes import router as crud_router

router = APIRouter()
router.include_router(crud_router)
router.include_router(pipeline_router)

__all__ = ["register_exception_handlers", "router"]
