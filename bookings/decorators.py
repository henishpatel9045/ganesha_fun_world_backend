from django.http import HttpResponse
from functools import wraps

from custom_auth.models import User


def user_type_required(user_types: list[str] = []):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            request = self.request
            user: User = request.user
            if user.user_type in user_types:
                return func(self, *args, **kwargs)
            else:
                return HttpResponse("Unauthorized", status=401)

        return wrapper

    return decorator
