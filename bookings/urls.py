from django.urls import path

from .views import (
    BookingFormView,
    PaymentFormView,
    BookingSummaryCardTemplateView,
    BookingEditFormView,
    BookingTicketTemplateView,
)


urlpatterns = [
    path("booking/", BookingFormView.as_view(), name="booking"),
    path(
        "booking/<str:booking_id>",
        BookingEditFormView.as_view(),
        name="booking_edit",
    ),
    path(
        "booking/<str:booking_id>/ticket",
        BookingTicketTemplateView.as_view(),
        name="booking_ticket",
    ),
    path(
        "booking/<str:booking_id>/summary",
        BookingSummaryCardTemplateView.as_view(),
        name="booking_summary",
    ),
    path(
        "booking/<str:booking_id>/payment",
        PaymentFormView.as_view(),
        name="booking_payment",
    ),
]
