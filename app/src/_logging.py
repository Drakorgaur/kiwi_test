import os
import logging

import structlog


def set_process_id(_, __, event_dict) -> dict:
    event_dict["process_id"] = os.getpid()

    return event_dict


def get_shared_processors() -> list:
    """Return shared processors for all loggers.

    structlog.processors.format_exc_info: Add exception info to the log record.
    structlog.processors.EventRenamer: Rename the key `event` to `message`.
    """
    return [
        structlog.processors.format_exc_info,
        set_process_id,
        structlog.processors.EventRenamer("message"),
    ]


# configure runtime logging
structlog.configure(
    processors=get_shared_processors() + [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)


def configure_logging():
    """Configure logging for uvicorn processes.

    The problem is that uvicorn should be run with CLI client.
    That blocks application to set uvicorn loggers to output a valid json-like log.
    So the application corrects loggers that are used by uvicorn processes to set new handlers and formatters.

    See thread:
        https://github.com/fastapi/fastapi/discussions/7457
    """
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=get_shared_processors(),
    )

    for logger in {"error", "access", "asgi"}:
        logger = logging.getLogger(f"uvicorn.{logger}")
        logger.handlers = []
        new_handler = logging.StreamHandler()
        new_handler.setFormatter(formatter)
        logger.addHandler(new_handler)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
