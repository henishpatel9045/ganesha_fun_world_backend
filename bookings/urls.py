from django.urls import path

from .views import (
    BookingHomeTemplateView,
    BookingFormView,
    PaymentFormView,
    BookingSummaryCardTemplateView,
    BookingEditFormView,
    BookingTicketTemplateView,
    BookingPaymentRecordsTemplateView,
    PaymentEditFormView,
)


urlpatterns = [
    path("", BookingHomeTemplateView.as_view(), name="booking_home"),
    path("booking/", BookingFormView.as_view(), name="booking_create"),
    path(
        "booking/<str:booking_id>",
        BookingEditFormView.as_view(),
        name="booking_edit",
    ),
    path(
        "payment/<str:payment_id>",
        PaymentEditFormView.as_view(),
        name="payment_edit",
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
    path(
        "booking/<str:booking_id>/payment-records",
        BookingPaymentRecordsTemplateView.as_view(),
        name="booking_payment_records",
    ),
]
