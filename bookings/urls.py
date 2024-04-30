from django.urls import path

from .views import whatsapp_handler, BookingFormView


urlpatterns = [
    path("whatsapp/", whatsapp_handler, name="whatsapp"),
    path("booking/", BookingFormView.as_view(), name="booking"),
]
