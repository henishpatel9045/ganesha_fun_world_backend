from django.urls import path

from .views import whatsapp_handler


urlpatterns = [
    path('whatsapp/', whatsapp_handler, name='whatsapp'),
]