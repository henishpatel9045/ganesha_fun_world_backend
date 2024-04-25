"""
ASGI config for ganesha_fun_world_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

if os.environ.get("ENVIRONMENT", 'test') == "prod":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ganesha_fun_world_backend.settings.prod')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ganesha_fun_world_backend.settings.test')

application = get_asgi_application()
