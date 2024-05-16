from .common import *


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://test_redis:6379",
    }
}

# RQ settings
RQ_QUEUES = {
    "default": {
        "HOST": "test_redis",
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 360,
    },
    "high": {
        "HOST": "test_redis",
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 500,
    },
    # "low": {
    #     "HOST": "redis",
    #     "PORT": 6379,
    #     "DB": 0,
    # },
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
            "filename": BASE_DIR / "logs" / "test-general.log",
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
        'weasyprint': { 
            'handlers': [],
            'level': 'WARNING', 
            'propagate': False,  # Prevent logs from being propagated to the root logger
        },
        'fontTools.subset': { 
            'handlers': [],
            'level': 'WARNING',
            'propagate': False,  # Prevent logs from being propagated to the root logger
        },
        "": {"handlers": ["file"], "level": os.environ.get("LOG_LEVEL", "INFO")},
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
