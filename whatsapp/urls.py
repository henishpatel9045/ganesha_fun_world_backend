from django.urls import path

from .views import WhatsAppWebhook, WhatsAppTestTriggerAPIView


urlpatterns = [
    path("webhook/", WhatsAppWebhook.as_view(), name="whatsapp_webhook"),
    path("trigger/", WhatsAppTestTriggerAPIView.as_view(), name="whatsapp_trigger"),
]
