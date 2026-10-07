import asyncio
import logging

import httpx
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from api.agents.sales_sql_agent import engine as sales_engine
from api.config import settings
from api.db.session import engine as primary_engine
from api.db.session import ping

logger = logging.getLogger("api.startup")

# covers the window between `docker-compose up` starting the api container
# and postgres/ollama finishing their own boot (ollama has no compose healthcheck)
MAX_ATTEMPTS = 10
WAIT_SECONDS = 2


class StartupCheckError(RuntimeError):
    """Raised when a required resource is still unreachable after all retries."""


def _retrying():
    return retry(
        stop=stop_after_attempt(MAX_ATTEMPTS),
        wait=wait_fixed(WAIT_SECONDS),
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.WARNING),
        reraise=True,
    )


@_retrying()
def _check_db(target_engine) -> None:
    ping(target_engine)


@_retrying()
async def _check_ollama() -> None:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url)
        response.raise_for_status()


async def run_startup_checks() -> None:
    db_checks = {
        "primary database": primary_engine,
        "sales read-only database": sales_engine,
    }
    for name, target_engine in db_checks.items():
        try:
            await asyncio.to_thread(_check_db, target_engine)
        except Exception as exc:
            raise StartupCheckError(f"{name} is unreachable: {exc}") from exc

    try:
        await _check_ollama()
    except Exception as exc:
        raise StartupCheckError(
            f"Ollama server at {settings.ollama_base_url} is unreachable: {exc}"
        ) from exc

    logger.info("startup checks passed: primary db, sales db, ollama")


def dispose_engines() -> None:
    primary_engine.dispose()
    sales_engine.dispose()
    logger.info("disposed database connection pools")
