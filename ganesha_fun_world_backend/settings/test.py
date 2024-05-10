from .common import *

INSTALLED_APPS += [
    "debug_toolbar",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]


INTERNAL_IPS = [
    "127.0.0.1",
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