import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)

    formatter = JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,
    )
