from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache
from decouple import config, Csv
import django_rq
import logging
import os

from common_config.common import CURRENT_ENVIRONMENT

from .messages.message_handlers import (
    handle_booking_session_messages,
    handle_sending_booking_ticket,
    handle_whatsapp_inquiry_message,
    send_daily_review_message,
    send_date_list_message,
    send_my_bookings_message,
    send_welcome_message,
    whatsapp_config,
)


TESTING_NUMBERS = config("WA_TEST_NUMBERS", cast=Csv())
CONVERSATION_TIMEOUT = 24*60*60

logging.getLogger(__name__)
high_queue = django_rq.get_queue("high")


class WhatsAppTestTriggerAPIView(APIView):
    def get(self, request):
        """
        Function to handle the get request.
        """
        try:
            secret = request.GET.get("secret")
            if secret != "secret9045":
                return Response(
                    {"message": "Invalid Secret"}, status=status.HTTP_200_OK
                )
            recipient_number = request.GET.get("number")
            send_welcome_message(recipient_number)
            return Response(200)
        except Exception as e:
            logging.exception(e)
            return Response(200)


class DailyReviewReminderAPIView(APIView):
    def get(self, request):
        """
        Function to handle the get request.
        """
        try:
            send_daily_review_message()
            return Response(200)
        except Exception as e:
            logging.exception(e)
            return Response(500)


class WhatsAppWebhook(APIView):
    """
    Class to handle the webhook for WhatsApp.
    """

    def get_message(self, data: dict) -> str | None:
        message = None
        entry = data.get("entry", [])
        if entry:
            changes = entry[0].get("changes", [])
            if changes:
                value = changes[0].get("value")
                if value:
                    message_tmp = value.get("messages")
                    if message_tmp:
                        message = message_tmp[0]
        return message

    def get(self, request):
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == config("WA_WEBHOOK_SECRET"):
                return Response(int(challenge), status=status.HTTP_200_OK)
        return Response(status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        """
        Function to handle the post request.
        """
        try:
            data = request.data
            message = self.get_message(data)
            if not message:
                return Response(200)
            sender = message["from"]
            received_msg_id = message["id"]
            msg_context = {
                "message_id": received_msg_id,
            }
            # TODO updated the below line to handle the test environment remove the testing condition
            if CURRENT_ENVIRONMENT == "test" and sender not in TESTING_NUMBERS:
                return Response(200)
            message_payload, message_type = "", ""

            cache.set(f"active_{sender}", True, timeout=CONVERSATION_TIMEOUT)
            
            if message.get("text"):
                message_payload = message["text"]["body"]
                message_type = "text"
            elif message.get("interactive"):
                message_payload = message["interactive"].get("list_reply")
                if not message_payload:
                    message_payload = message["interactive"].get("button_reply")
                message_payload = message_payload["id"]
                message_type = "interactive"
            elif message.get("button"):
                message_payload = message["button"]["payload"]
                message_type = "button"

            if not message_payload or not message_type:
                return Response(400)

            logging.info(
                f"Message received from {sender}: {message_type}, {message_payload}"
            )

            try:
                active_session = cache.get(f"booking_session_{sender}")
                if active_session:
                    handle_booking_session_messages(
                        sender,
                        message_type,
                        message_payload,
                        active_session,
                        msg_context,
                    )
                    return Response(200)

                if message_payload == "booking_session_start":
                    cache.set(
                        f"booking_session_{sender}",
                        {
                            "wa_number": sender,
                        },
                        timeout=300,
                    )
                    send_date_list_message(sender, msg_context)
                    return Response(200)

                if message_payload.startswith("booking_ticket_"):
                    handle_sending_booking_ticket(
                        sender,
                        message_payload.replace("booking_ticket_", ""),
                        msg_context,
                    )
                    return Response(200)

                if message_payload == "my_bookings":
                    send_my_bookings_message(sender, msg_context)
                    return Response(200)

                if message_payload == "whatsapp_inquiry":
                    high_queue.enqueue(
                        handle_whatsapp_inquiry_message,
                        sender,
                    )
                    return Response(200)

                if message_payload.lower().startswith("hi"):
                    send_welcome_message(sender)
                    return Response(200)

                logging.warning(f"Unhandled message: data: {str(data)}")
                whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Sorry, I didn't understand that. Please try again by sending *Hi*."
                    },
                    msg_context,
                )
                return Response(200)
            except Exception as e:
                logging.exception(e)
                whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Sorry, there is some technical issue. Please try again later."
                    },
                    msg_context,
                )
                cache.delete(
                    f"booking_session_{sender}"
                )  # delete active booking if there is any.

                return Response(200)
        except Exception as e:
            logging.exception(e)

            return Response(500)
