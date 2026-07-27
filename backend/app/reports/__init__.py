"""The progress report feature: CRUD, uploads, AI generation, and PDF export.

app.main imports exactly two names from here: router and
register_exception_handlers.
"""

from .exception_handlers import register_exception_handlers
from .routes import router

__all__ = ["register_exception_handlers", "router"]
