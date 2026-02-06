import logging
import logging.config
import sys
import os

# Attempt to import python_json_logger, but don't fail if it's not there
# (though it should be, as we've added it to pyproject.toml)
try:
    from python_json_logger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False

DEFAULT_LOG_LEVEL = "INFO" # Ensure INFO level is on by default

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "python_json_logger.jsonlogger.JsonFormatter" if HAS_JSON_LOGGER else "logging.Formatter",
            "format": "%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s"
        }
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": sys.stdout,
        }
    },
    "root": {
        "handlers": ["console_json"],
        "level": DEFAULT_LOG_LEVEL,
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console_json"],
            "level": os.environ.get("UVICORN_LOG_LEVEL", "INFO").upper(),
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console_json"],
            "level": os.environ.get("UVICORN_ERROR_LOG_LEVEL", "INFO").upper(),
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console_json"],
            "level": os.environ.get("UVICORN_ACCESS_LOG_LEVEL", "WARNING").upper(), # Access logs can be noisy
            "propagate": False,
        },
        "fastapi": {
             "handlers": ["console_json"],
             "level": os.environ.get("FASTAPI_LOG_LEVEL", "INFO").upper(),
             "propagate": False,
        }
    }
}

# Fallback formatter if python_json_logger is not available
if not HAS_JSON_LOGGER:
    LOGGING_CONFIG["formatters"]["json"]["format"] = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    # Consider logging a warning that json logger is not available
    # logging.warning("python-json-logger not found, falling back to standard formatter.")

_logging_configured = False

def setup_logging():
    """Initializes logging configuration for the application."""
    global _logging_configured
    logging.config.dictConfig(LOGGING_CONFIG)
    _logging_configured = True
    # Optional: Log that configuration is done, but be careful about logging before config is fully applied.
    # initial_logger = logging.getLogger(__name__)
    # initial_logger.info("Logging configured using dictConfig.")

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger instance with the given name.
    Ensures logging is configured on the first call.
    """
    global _logging_configured
    if not _logging_configured:
        setup_logging()
    return logging.getLogger(name)
