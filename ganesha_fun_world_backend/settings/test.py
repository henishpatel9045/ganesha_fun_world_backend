from .common import *


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "crispy_forms",
    "crispy_bootstrap5",
    "rest_framework",
    "django_rq",
    "drf_yasg",
    "import_export",
    # "silk",
    "custom_auth",
    "frontend",
    "management_core",
    "bookings",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "silk.middleware.SilkyMiddleware",
]

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
        "DEFAULT_TIMEOUT": 600,
    },
    "high": {
        "HOST": "test_redis",
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 600,
    },
    "low": {
        "HOST": "test_redis",
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

SILKY_PYTHON_PROFILER = True
SILKY_AUTHENTICATION = True 
