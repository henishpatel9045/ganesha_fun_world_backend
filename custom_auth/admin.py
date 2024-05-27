from collections.abc import Sequence
from typing import Any
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.http import HttpRequest

from custom_auth.forms import CustomUserCreationForm
from .models import User

# Register your models here.


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = CustomUserCreationForm

    def get_list_display(self, request: HttpRequest) -> Sequence[str]:
        res = list(super().get_list_display(request))
        res.insert(2, "user_type")
        return res

    def get_fieldsets(
        self, request: HttpRequest, obj: Any | None = ...
    ) -> list[tuple[str | None, dict[str, Any]]]:
        return list(super().get_fieldsets(request, obj)) + [
            (None, {"fields": ("user_type",)}),
        ]
