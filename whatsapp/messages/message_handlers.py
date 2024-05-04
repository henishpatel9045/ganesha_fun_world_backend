from datetime import timedelta
from pprint import pprint
from django.utils import timezone
from django.core.cache import cache
import requests
import os
from whatsapp.utils import WhatsAppClient

LOGO_URL = os.environ.get(
    "LOGO_URL", "https://www.shreeganeshafunworld.com/images/logo.png"
)


whatsapp_config = WhatsAppClient(
    "EAAGuKjgErkMBO7ErSUZCjE0Pz5EgloaJ88MVoXZCdSVvvrgcOX203wQwnf42oYM4xvZCVsxcLFXWje607IHqSaVc6kysrMXO95DR4VkSx2Pyqf3FJujMXKm6UwMg5vcFmL4poOg1GRsh5RpcluZALphdOLt88CdPIZAFm3hVTdXSMVctrMvkG7IfZCB14X9swCVSQDCWWLUceTLn0z8PQZD",
    "285776191286365",
)
client = whatsapp_config.get_client()


def send_date_list_message(recipient_number: str) -> requests.Response:
    """
    Function to send date list message to the user.

    :param `recipient_number`: The number to which message is to be sent
    """
    response_payload = {
        "type": "list",
        "body": {"text": "Please select date for booking"},
        "action": {
            "button": "Select Date",
            "sections": [
                {
                    "title": "Available Dates",
                    "rows": [
                        {
                            "id": (timezone.now().date() + timedelta(days=i)).strftime("%d-%m-%Y"),
                            "title": (timezone.now().date() + timedelta(days=i)).strftime("%d %b %Y"),
                            # "description": "",
                        }
                        for i in range(1, 11)
                    ],
                },
            ],
        },
    }
    pprint(response_payload)
    return whatsapp_config.send_message(
        recipient_number, "interactive", response_payload
    )


def send_welcome_message(recipient_number: str) -> requests.Response:
    """
    Function to send welcome message to the user.

    :param `recipient_number`: The number to which message is to be sent

    template_name used is `welcome_message`
    """
    payload = {
        "name": "welcome_action",
        "language": {"code": "en"},
        "components": [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {
                            "link": "https://www.shreeganeshafunworld.com/images/logo.png"
                        },
                    }
                ],
            },
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": "0",
                "parameters": [{"type": "payload", "payload": "whatsapp_inquiry"}],
            },
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": "1",
                "parameters": [
                    {"type": "payload", "payload": "booking_session_start"}
                ],
            },
        ],
    }
    return whatsapp_config.send_message(recipient_number, "template", payload)


def handle_booking_session_messages(
    sender: str, message_type: str, payload: str, active_session: dict
) -> requests.Response:
    """
    Function to handle booking session messages.

    :param `sender`: The sender of the message
    :param `message_type`: The type of the message i.e. `text`, `button`, `interactive`
    :param `payload`: The payload of the message
    """

    if payload == "booking_session_cancel":
        cache.delete(f"booking_session_{sender}")
        return whatsapp_config.send_message(
            sender,
            "text",
            {"body": "Booking session cancelled. Please send Hi to start again."},
        )

    if active_session.get("date") is None:
        if message_type == "interactive":
            if timezone.datetime.strptime(payload, "%d-%m-%Y").date() - timezone.now().date() <= timedelta(days=0):
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {"body": "Please select a valid date for booking."},
                )
            active_session["date"] = payload
            cache.set(f"booking_session_{sender}", active_session, timeout=300)
            return whatsapp_config.send_message(
                sender,
                "text",
                {"body": f"Enter total number of *Adults (Male)* age *more than 10*."},
            )
    elif active_session.get("adult_male") is None:
        if message_type == "text":
            value = payload.isnumeric()
            print("INSIDE SET MALE: ", payload)
            if value:
                value = int(payload)
                if value >= 0:
                    active_session["adult_male"] = value
                    cache.set(f"booking_session_{sender}", active_session, timeout=300)
                    return whatsapp_config.send_message(
                        sender,
                        "text",
                        {
                            "body": f"Enter total number of *Adults (Female)* age *more than 10 years*."
                        },
                    )
            else:
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Enter a valid number of Male Adults (it's value can only be 0 or more)",
                    },
                )

    elif active_session.get("adult_female") is None:
        if message_type == "text":
            value = payload.isnumeric()
            print("INSIDE SET FEMALE: ", payload)
            if value:
                value = int(payload)
                if value >= 0:
                    active_session["adult_female"] = value
                    cache.set(f"booking_session_{sender}", active_session, timeout=300)
                    return whatsapp_config.send_message(
                        sender,
                        "text",
                        {
                            "body": f"Enter total number of *Children* age between *5 - 10 years*.",
                        },
                    )
            else:
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Please enter a valid number of Female Adults (it's value can only be 0 or more)",
                    },
                )

    elif active_session.get("child") is None:
        if message_type == "text":
            value = payload.isnumeric()
            print("INSIDE SET CHILD: ", payload)
            if value:
                value = int(payload)
                if value >= 0:
                    active_session["child"] = value
                    cache.set(f"booking_session_{sender}", active_session, timeout=300)
                    return whatsapp_config.send_message(
                        sender,
                        "text",
                        {
                            "body": f"Enter total number of *Infants* age between *0 - 5 years*.",
                        },
                    )
            else:
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Please enter a valid number of Child (it's value can only be 0 or more)"
                    },
                )

    elif active_session.get("infant") is None:
        if message_type == "text":
            value = payload.isnumeric()
            print("INSIDE SET INFANT: ", payload)
            if value:
                value = int(payload)
                if value >= 0:
                    # Handle the validation logic for booking here
                    if (
                        active_session["adult_female"] <= 0
                        and active_session["child"] <= 0
                    ):
                        cache.delete(f"booking_session_{sender}")
                        return whatsapp_config.send_message(
                            sender,
                            "text",
                            {
                                "body": "At least one female adult or child is required for booking. Send Hi to start again.",
                            },
                        )

                    if (
                        active_session["adult_male"] <= 0
                        and active_session["adult_female"] <= 0
                    ):
                        cache.delete(f"booking_session_{sender}")
                        return whatsapp_config.send_message(
                            sender,
                            "text",
                            {
                                "body": "At least one adult is required for booking. Send Hi to start again.",
                            },
                        )

                    active_session["infant"] = value
                    cache.set(f"booking_session_{sender}", active_session, timeout=300)
                    return whatsapp_config.send_message(
                        sender,
                        "text",
                        {
                            "body": f"Your booking details are as follows:\n*Date*: {active_session.get("date")}\n*Adults (Male)*: {active_session.get("adult_male")}\n*Adults (Female)*: {active_session.get("adult_female")}\n*Children*: {active_session.get("child")}\n*Infants*: {active_session.get("infant")}",
                        },
                    )
            else:
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Please enter a valid number of Male Adults (it's value can only be 0 or more)"
                    },
                )

    cache.delete(f"booking_session_{sender}")
    return whatsapp_config.send_message(
        sender,
        "text",
        {
            "body": "Invalid message your booking session is terminated. Please send Hi to start again.",
        },
    )
