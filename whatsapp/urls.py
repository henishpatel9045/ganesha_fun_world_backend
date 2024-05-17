from django.urls import path

from .views import (
    WhatsAppWebhook,
    WhatsAppTestTriggerAPIView,
    DailyReviewReminderAPIView,
)


urlpatterns = [
    path("webhook/", WhatsAppWebhook.as_view(), name="whatsapp_webhook"),
    path("trigger/", WhatsAppTestTriggerAPIView.as_view(), name="whatsapp_trigger"),
    path(
        "review-reminder/", DailyReviewReminderAPIView.as_view(), name="review_reminder"
    ),
]
