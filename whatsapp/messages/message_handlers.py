from datetime import timedelta
from pprint import pprint
from django.utils import timezone
from django.core.cache import cache
import requests
import os

from whatsapp.utils import WhatsAppClient
from bookings.utils import create_or_update_booking, create_razorpay_order


LOGO_URL = os.environ.get(
    "LOGO_URL", "https://www.shreeganeshafunworld.com/images/logo.png"
)


whatsapp_config = WhatsAppClient(
    "EAAGuKjgErkMBOZCltUf7TTRiHywvED8e61yajhK6yZCiF8k05ZBX1IptAmFkAxQTdtExAReRZBVEDPHbRMYGERmLj18tZBNZBqgF6IQLWZBrc0CtGjZAmrQAaZAfHSeKvV9C3FzRqnTQso8F1yLJsQflZCPGhfpKn7JJxDHRxmB9hgrOd2InIPh0JsjfUF9gVXIbnh6gfopK6GC3ws1tkrlPBL",
    "285776191286365",
)
client = whatsapp_config.get_client()


def send_date_list_message(recipient_number: str, context: dict|None) -> requests.Response:
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
    return whatsapp_config.send_message(
        recipient_number, "interactive", response_payload, context
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
    sender: str, message_type: str, payload: str, active_session: dict, msg_context: dict | None
) -> requests.Response:
    """
    Function to handle booking session messages.

    :param `sender`: The sender of the message
    :param `message_type`: The type of the message i.e. `text`, `button`, `interactive`
    :param `payload`: The payload of the message
    :param `active_session`: The active booking session of the user
    :param `msg_context`: The context of the message i.e. for replying to msg
    """

    if payload == "booking_session_cancel":
        cache.delete(f"booking_session_{sender}")
        return whatsapp_config.send_message(
            sender,
            "text",
            {"body": "Booking session cancelled. Please send Hi to start again."},
            msg_context
        )
        
    # Handle the logic after booking is confirmed i.e. create booking instance and generate razorpay order for the same.
    if message_type == "interactive" and payload == "booking_session_confirm":
        # Create booking
        try:
            booking = create_or_update_booking(
                wa_number=active_session.get("wa_number"),
                date=timezone.datetime.strptime(active_session.get("date"), "%d-%m-%Y").date(),
                adult_male=active_session.get("adult_male"),
                adult_female=active_session.get("adult_female"),
                child=active_session.get("child"),
                booking_costume_data={},
                booking_type="whatsapp_booking"
            )
            order = create_razorpay_order(booking.total_amount, booking.wa_number, {
                "id": str(booking.id),
                "amount": str(booking.total_amount),
                "adult_male": str(booking.adult_male),
                "adult_female": str(booking.adult_female),
                "child": str(booking.child)
            })
            print(order)
            res = whatsapp_config.send_message(
                sender,
                "text",
                {"preview_url": True,"body": f"Booking confirmed.\nMake payment by click on this link in next 15 minutes \n{order}"}, msg_context)
            
            return res
        except Exception as e:
            return whatsapp_config.send_message(
                sender,
                "text",
                {"body": f"Sorry for inconvenience. Error occurred while creating booking: {str(e)}"},
                msg_context
            )
        

    if active_session.get("date") is None:
        if message_type == "interactive":
            if timezone.datetime.strptime(payload, "%d-%m-%Y").date() - timezone.now().date() <= timedelta(days=0):
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {"body": "Please select a valid date for booking."},
                    msg_context
                )
            active_session["date"] = payload
            cache.set(f"booking_session_{sender}", active_session, timeout=300)
            return whatsapp_config.send_message(
                sender,
                "text",
                {"body": f"Enter total number of *Adults (Male)* age *more than 10*."},
                msg_context
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
                        msg_context
                    )
            else:
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Enter a valid number of Male Adults (it's value can only be 0 or more)",
                    },
                    msg_context
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
                        msg_context
                    )
            else:
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Please enter a valid number of Female Adults (it's value can only be 0 or more)",
                    },
                    msg_context
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
                        msg_context
                    )
            else:
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Please enter a valid number of Child (it's value can only be 0 or more)"
                    },
                    msg_context
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
                            msg_context
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
                            msg_context
                        )

                    active_session["infant"] = value
                    cache.set(f"booking_session_{sender}", active_session, timeout=300)
                    return whatsapp_config.send_message(
                        sender,
                        "interactive",
                        {
                            "type": "button",
                            "body": {
                            "text": f"Your booking details are as follows:\n*Date*: {active_session.get("date")}\n*Adults (Male)*: {active_session.get("adult_male")}\n*Adults (Female)*: {active_session.get("adult_female")}\n*Children*: {active_session.get("child")}\n*Infants*: {active_session.get("infant")}",
                            },
                            "action": {
                            "buttons": [
                                {
                                "type": "reply",
                                "reply": {
                                    "id": "booking_session_confirm",
                                    "title": "Confirm Booking"
                                }
                                }
                            ]
                            }
                        },
                        msg_context
                    )
            else:
                return whatsapp_config.send_message(
                    sender,
                    "text",
                    {
                        "body": "Please enter a valid number of Male Adults (it's value can only be 0 or more)"
                    },
                    msg_context
                )

    # cache.delete(f"booking_session_{sender}")
    return whatsapp_config.send_message(
        sender,
        "interactive",
        {
            "type": "button",
            "body": {
            "text": "Invalid message. If you want to cancel your booking please click on below button."
            },
            "action": {
            "buttons": [
                {
                "type": "reply",
                "reply": {
                    "id": "booking_session_cancel",
                    "title": "Cancel Booking"
                }
                }
            ]
            }
        },
        msg_context
    )
