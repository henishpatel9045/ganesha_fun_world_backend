from django.contrib.auth.models import AbstractUser
from django.db import models

from common_config.common import BOUNCER_USER, USER_TYPES


class User(AbstractUser):
    user_type = models.CharField(
        max_length=100, choices=USER_TYPES, default=BOUNCER_USER
    )
    pass
