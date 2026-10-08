from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.core.logging import configure_logging
from api.core.middleware import RequestLogMiddleware, register_exception_handlers
from api.core.startup import dispose_engines, run_startup_checks
from api.routes import access, chat, feedback


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure logging and run startup checks before serving, then dispose engines on shutdown.

    Args:
        app: The FastAPI application instance (unused, required by the lifespan signature).
    """
    configure_logging()
    await run_startup_checks()
    yield
    dispose_engines()


def create_app() -> FastAPI:
    """Build the FastAPI application with middleware, exception handlers, and routers registered.

    Returns:
        The configured FastAPI application instance.
    """
    app = FastAPI(title="Knowledge System API", lifespan=lifespan)
    app.add_middleware(RequestLogMiddleware)
    register_exception_handlers(app)
    # chat with agent functions
    app.include_router(chat.router)
    # permission control api: validate access
    app.include_router(access.router)
    # write back feedbackloop
    app.include_router(feedback.router)
    return app


app = create_app()
