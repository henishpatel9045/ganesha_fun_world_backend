from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache
from decouple import config, Csv

import pprint
from .utils import WhatsAppClient
from .messages.message_handlers import (
    handle_booking_session_messages,
    send_date_list_message,
    send_welcome_message,
)


whatsapp_config = WhatsAppClient(
    "EAAGuKjgErkMBO7ErSUZCjE0Pz5EgloaJ88MVoXZCdSVvvrgcOX203wQwnf42oYM4xvZCVsxcLFXWje607IHqSaVc6kysrMXO95DR4VkSx2Pyqf3FJujMXKm6UwMg5vcFmL4poOg1GRsh5RpcluZALphdOLt88CdPIZAFm3hVTdXSMVctrMvkG7IfZCB14X9swCVSQDCWWLUceTLn0z8PQZD",
    "285776191286365",
)

TESTING_NUMBERS = config("WA_TEST_NUMBERS", cast=Csv())


class WhatsAppTestTriggerAPIView(APIView):
    def get(self, request):
        """
        Function to handle the get request.
        """
        res = send_welcome_message("917990577979")
        pprint.pprint(res.json())
        return Response("Hello, World!", status=status.HTTP_200_OK)


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
            if mode == "subscribe" and token == "secret9045":
                return Response(int(challenge), status=status.HTTP_200_OK)
        return Response(status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        """
        Function to handle the post request.
        """
        data = request.data
        message = self.get_message(data)
        if not message:
            return Response(200)
        sender = message["from"]
        # TODO remove below line to enable production i.e. remove reply only to testing numbers feature
        if sender not in TESTING_NUMBERS:
            return Response(200)
        message_payload, message_type = "", ""

        if message.get("text"):
            message_payload = message["text"]["body"]
            message_type = "text"
        elif message.get("interactive"):
            message_payload = message["interactive"]["list_reply"]["id"]
            message_type = "interactive"
        elif message.get("button"):
            message_payload = message["button"]["payload"]
            message_type = "button"

        if not message_payload or not message_type:
            return Response(400)

        print("+" * 50)
        print("PAYLOAD: ", message_payload)
        print("+" * 50)

        active_session = cache.get(f"booking_session_{sender}")
        if active_session:
            handle_booking_session_messages(
                sender, message_type, message_payload, active_session
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
            send_date_list_message(sender)
            return Response(200)

        print("SENDER: ", sender)
        pprint.pprint(data)
        print("-" * 50)
        return Response(200)
