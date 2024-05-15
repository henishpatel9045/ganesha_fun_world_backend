from typing import Any
from django.contrib.auth.forms import UserCreationForm

from .models import User


class CustomUserCreationForm(UserCreationForm):
    def save(self, commit: bool = ...) -> Any:
        user: User = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_staff = True
        user.is_superuser = False
        if commit:
            user.save()
            user.user_permissions.all().delete()
            user.save()
            if hasattr(self, "save_m2m"):
                self.save_m2m()
        return user

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "user_type",
        )
