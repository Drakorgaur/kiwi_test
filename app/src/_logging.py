import logging

import structlog


def get_shared_processors() -> list:
    return [
        structlog.processors.format_exc_info,
        structlog.processors.EventRenamer("message"),
    ]


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
