from django.urls import path

from .views import (
    LockerReturnFormView,
    qr_code_homepage_redirect,
    AdminDataDashboard,
    AdminDashboardTemplateView,
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
    CostumeHomeTemplateView,
    CostumeSummaryTemplateView,
    CronHandlerAPIView,
    IssueCostumesAPIView,
    BookingCostumeReturnFormView,
    BouncerSummaryCardTemplateView,
    CanteenCardFormView,
    LockerSummaryTemplateView,
    LockerAddFormView,
    LockerEditFormView,
)


urlpatterns = [
    path("", BookingHomeTemplateView.as_view(), name="booking_home"),
    path("dashboard", AdminDashboardTemplateView.as_view(), name="admin_dashboard"),
    path("api/dashboard", AdminDataDashboard.as_view(), name="admin_dashboard_api"),
    path("costume", CostumeHomeTemplateView.as_view(), name="costume_home"),
    path("qr-redirect/<str:booking_id>", qr_code_homepage_redirect, name="qr_redirect"),
    path(
        "razorpay/webhook/",
        RazorpayPaymentWebhookAPIView.as_view(),
        name="razorpay_payment_webhook",
    ),
    path("booking/", BookingFormView.as_view(), name="booking_create"),
    path("history/", BookingHistoryTemplateView.as_view(), name="booking_history"),
    path("cron-handler/", CronHandlerAPIView.as_view(), name="cron_handler"),
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
    path(
        "booking/<str:booking_id>/bouncer/summary",
        BouncerSummaryCardTemplateView.as_view(),
        name="bouncer_ticket_summary",
    ),
    path(
        "booking/<str:booking_id>/canteen/card",
        CanteenCardFormView.as_view(),
        name="canteen_card",
    ),
    path(
        "booking/<str:booking_id>/locker/summary",
        LockerSummaryTemplateView.as_view(),
        name="locker_summary",
    ),
    path(
        "booking/<str:booking_id>/locker/add",
        LockerAddFormView.as_view(),
        name="locker_add",
    ),
    path(
        "booking/<str:booking_id>/locker/edit",
        LockerEditFormView.as_view(),
        name="locker_edit",
    ),
    path(
        "booking/<str:booking_id>/locker/return",
        LockerReturnFormView.as_view(),
        name="locker_return",
    ),
]
