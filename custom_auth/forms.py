from typing import Any
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Permission
import logging

from .models import User
from common_config.common import LOCKER_MANAGER_USER


logging.getLogger(__name__)


class CustomUserCreationForm(UserCreationForm):
    def save(self, commit: bool = ...)  -> Any:
        user: User = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_staff = True
        user.is_superuser = False
        user.save()
        user.user_permissions.all().delete()
        
        if user.user_type == LOCKER_MANAGER_USER:
            permissions = Permission.objects.filter(codename__in=[
                'add_locker', 'change_locker', 'delete_locker', 'view_locker'
            ])
            user.user_permissions.add(*permissions)
        if hasattr(self, "save_m2m"):
            self.save_m2m()
        return user

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "user_type",
        )
