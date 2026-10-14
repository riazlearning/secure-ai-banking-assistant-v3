import logging

from banking_assistant.infrastructure.logging_config import configure_logging


configure_logging()

logger = logging.getLogger("banking_assistant")

logger.info(
    "Transfer validation started",
    extra={
        "event": "transfer_validation_started",
        "service": "banking-assistant",
    },
)
