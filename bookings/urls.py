from django.urls import path

from .views import (
    RazorpayPaymentWebhookAPIView,
    BookingHomeTemplateView,
    BookingFormView,
    PaymentFormView,
    BookingSummaryCardTemplateView,
    BookingEditFormView,
    BookingTicketTemplateView,
    BookingPaymentRecordsTemplateView,
    PaymentEditFormView,
    BookingHistoryTemplateView,
    SaveBookingTicketAPIView,
    CostumeSummaryTemplateView,
    IssueCostumesAPIView,
    BookingCostumeReturnFormView,
)


urlpatterns = [
    path("", BookingHomeTemplateView.as_view(), name="booking_home"),
    path(
        "razorpay/webhook/",
        RazorpayPaymentWebhookAPIView.as_view(),
        name="razorpay_payment_webhook",
    ),
    path("booking/", BookingFormView.as_view(), name="booking_create"),
    path("history/", BookingHistoryTemplateView.as_view(), name="booking_history"),
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
        "booking/<str:booking_id>/generate-ticket",
        SaveBookingTicketAPIView.as_view(),
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
    path(
        "booking/<str:booking_id>/costume/summary",
        CostumeSummaryTemplateView.as_view(),
        name="costume_summary",
    ),
    path(
        "booking/<str:booking_id>/costume/issue-all",
        IssueCostumesAPIView.as_view(),
        name="costume_issue_all",
    ),
    path(
        "booking/<str:booking_id>/costume/return",
        BookingCostumeReturnFormView.as_view(),
        name="costume_return",
    ),
]
