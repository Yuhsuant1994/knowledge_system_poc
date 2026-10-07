import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from api.config import settings

FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        log_dir / "api.log", when="midnight", backupCount=14
    )
    stream_handler = logging.StreamHandler(sys.stdout)

    logging.basicConfig(
        level=settings.log_level,
        format=FORMAT,
        handlers=[stream_handler, file_handler],
        force=True,
    )
