import logging
import logging.config

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(level: str = "INFO") -> None:
    stderr_console = Console(stderr=True)
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "rich": {
                    "format": "%(message)s",
                    "datefmt": "[%X]",
                },
            },
            "handlers": {
                "console": {
                    "()": RichHandler,
                    "console": stderr_console,
                    "show_time": True,
                    "show_level": True,
                    "show_path": False,
                    "rich_tracebacks": True,
                    "markup": False,
                    "formatter": "rich",
                },
            },
            "root": {
                "level": level,
                "handlers": ["console"],
            },
        }
    )
