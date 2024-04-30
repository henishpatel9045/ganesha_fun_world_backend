from django.urls import path

from .views import BookingFormView


urlpatterns = [
    path("booking/", BookingFormView.as_view(), name="booking"),
]
