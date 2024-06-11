from .common import *

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://redis:6379",
    }
}

# RQ settings
RQ_QUEUES = {
    "default": {
        "HOST": "redis",
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 600,
    },
    "high": {
        "HOST": "redis",
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 600,
    },
    "low": {
        "HOST": "redis",
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 10000,
    },
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": "midnight",
            "backupCount": 15,
            "filename": BASE_DIR / "logs" / "prod-general.log",
            "formatter": "verbose",
        },
        "rq_console": {
            "level": "DEBUG",
            "class": "rq.logutils.ColorizingStreamHandler",
            "formatter": "rq_console",
            "exclude": ["%(asctime)s"],
        },
    },
    "loggers": {
        "rq.worker": {"handlers": ["rq_console"], "level": "DEBUG"},
        "weasyprint": {
            "handlers": [],
            "level": "WARNING",
            "propagate": False,  # Prevent logs from being propagated to the root logger
        },
        "fontTools.subset": {
            "handlers": [],
            "level": "WARNING",
            "propagate": False,  # Prevent logs from being propagated to the root logger
        }, 
        "django": {"handlers": ["file"], "level": "DEBUG"},
        "": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[{asctime}]: ({levelname}) {name} $ {message} $ {pathname} #{funcName}:L{lineno}",
            "style": "{",
        },
        "rq_console": {
            "format": "%(asctime)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
}
