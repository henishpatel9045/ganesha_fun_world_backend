from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
import requests
import os
import logging
import django_rq
from django_rq.queues import get_queue

from bookings.models import Booking, Payment
from common_config.common import ADVANCE_PER_PERSON_AMOUNT_FOR_BOOKING, HOST_URL
from whatsapp.utils import WhatsAppClient
from management_core.models import TicketPrice, WhatsAppInquiryMessage
from bookings.utils import create_or_update_booking, create_razorpay_order, razorpay_client
from bookings.ticket.utils import generate_ticket_pdf

logging.getLogger(__name__)

LOGO_URL = os.environ.get(
    "LOGO_URL", "https://www.shreeganeshafunworld.com/images/logo.png"
)
USE_TEMPLATE_MESSAGE_BOOKING_TICKET = int(os.environ.get("USE_TEMPLATE_MESSAGE_BOOKING_TICKET", 0)) == 1


whatsapp_config = WhatsAppClient(
    os.environ.get("WA_SECRET_KEY"),
    os.environ.get("WA_PHONE_ID"),
)
client = whatsapp_config.get_client()

def delete_booking_session(sender: str):
    cache.delete(f"booking_session_{sender}")


def send_date_list_message(recipient_number: str, context: dict|None) -> requests.Response:
    """
    Function to send date list message to the user.

    :param `recipient_number`: The number to which message is to be sent
    """
    available_dates = list(TicketPrice.objects.filter(date__gt=timezone.now().date()).order_by("date")[:10].values_list("date", flat=True))
    logging.info(f"Available Dates: {available_dates}")
    
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
                            "id": date.strftime("%d-%m-%Y"),
                            "title": date.strftime("%d %b %Y"),
                            # "description": "",
                        }
                        for date in available_dates
                    ],
                },
            ],
        },
    }
    if available_dates:
        res = whatsapp_config.send_message(
            recipient_number, "interactive", response_payload, context
        )
    else:
        res = whatsapp_config.send_message(
            recipient_number, "text", {"body": "No dates available for booking."}, context
        )
        delete_booking_session(recipient_number)
    return res


def send_welcome_message(recipient_number: str) -> requests.Response:
    """
    Function to send welcome message to the user.

    :param `recipient_number`: The number to which message is to be sent

    template_name used is `welcome_message`
    """
    payload = {
        "name": "welcome_action_template",
        "language": {"code": "en"},
        "components": [
            {
                "type": "header",
                "parameters": [
                    {
                        "type": "image",
                        "image": {
                            "link": f"{HOST_URL}/static/images/logo.png"
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
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": "2",
                "parameters": [
                    {"type": "payload", "payload": "my_bookings"}
                ],
            },
        ],
    }
    return whatsapp_config.send_message(recipient_number, "template", payload).json()


def confirm_razorpay_payment(payment_link_id: str, available_tries: int = 3) -> str:
    try:
        response = razorpay_client.payment_link.fetch(payment_link_id)
        if response.get("payments"):
            received_payment = response["payments"][0]
            if received_payment["status"] != "captured":
                return "Payment not captured"
        
            received_booking_id = response["notes"]["booking_id"]
            logging.info(f"Payment captured for booking: {received_booking_id}")
            booking = Booking.objects.get(id=received_booking_id)
            if booking.received_amount > 0:
                return f"Booking already paid and updated for booking_id: {received_booking_id}"
            total_persons = booking.adult_male + booking.adult_female + booking.child
            total_amount = total_persons * ADVANCE_PER_PERSON_AMOUNT_FOR_BOOKING

            received_amount = int(received_payment["amount"]) / 100
            if total_amount != received_amount:
                raise Exception("Amount mismatched")

            with transaction.atomic():
                payment = Payment()
                payment.booking = booking
                payment.payment_mode = "payment_gateway"
                payment.payment_for = "booking"
                payment.amount = received_amount
                payment.is_confirmed = True
                payment.payment_data = response
                payment.booking.received_amount += Decimal(payment.amount)
                payment.booking.save()
                payment.save()
            handle_sending_booking_ticket(booking.wa_number, "", None, booking)
            return "Payment confirmed successfully"
        RETRY_AFTER = [1,2,3,5,7]
        if available_tries > 0:
            scheduled_queue = get_queue("default")
            scheduled_queue.enqueue_in(
                timedelta(minutes=RETRY_AFTER[5-available_tries]),
                confirm_razorpay_payment,
                payment_link_id,
                available_tries - 1
            )
        return "No payment received for the payment link."
    except Exception as e:
        logging.exception(e)
        return "Payment not confirmed due to some error"


def handle_booking_session_confirm(active_session: dict, sender: str, msg_context: dict|None):
    try:
        booking = create_or_update_booking(
            wa_number=active_session.get("wa_number"),
            date=timezone.datetime.strptime(active_session.get("date"), "%d-%m-%Y").date(),
            adult_male=active_session.get("adult_male"),
            adult_female=active_session.get("adult_female"),
            child=active_session.get("child"),
            infant=active_session.get("infant", 0),
            booking_costume_data={},
            booking_type="whatsapp_booking"
        )
        total_persons = booking.adult_male + booking.adult_female + booking.child
        total_amount = ADVANCE_PER_PERSON_AMOUNT_FOR_BOOKING * total_persons
        order = create_razorpay_order(total_amount, booking.wa_number, booking)
        res = whatsapp_config.send_message(
            sender,
            "text",
            {"preview_url": True,"body": f"Booking confirmed.\nMake payment by click on this link in next 15 minutes \n{order["short_url"]}"}, msg_context)
        delete_booking_session(sender)
        scheduled_queue = get_queue("default")
        scheduled_queue.enqueue_in(
            timedelta(minutes=2),
            confirm_razorpay_payment,
            order["id"],
            5
        )
        return res
    except Exception as e:
        delete_booking_session(sender)
        return whatsapp_config.send_message(
            sender,
            "text",
            {"body": f"Sorry for inconvenience. Error occurred while creating booking: {str(e)}"},
            msg_context
        )

def handle_booking_session_messages(
    sender: str, message_type: str, payload: str, active_session: dict, msg_context: dict | None
) -> requests.Response | None:
    """
    Function to handle booking session messages.

    :param `sender`: The sender of the message
    :param `message_type`: The type of the message i.e. `text`, `button`, `interactive`
    :param `payload`: The payload of the message
    :param `active_session`: The active booking session of the user
    :param `msg_context`: The context of the message i.e. for replying to msg
    """

    if payload == "booking_session_cancel":
        delete_booking_session(sender)
        return whatsapp_config.send_message(
            sender,
            "text",
            {"body": "Booking session cancelled. Please send Hi to start again."},
            msg_context
        )
        
    # Handle the logic after booking is confirmed i.e. create booking instance and generate razorpay order for the same.
    if message_type == "interactive" and payload == "booking_session_confirm":
        # Create booking
        queue = django_rq.get_queue("high")
        queue.enqueue(
            handle_booking_session_confirm,
            active_session,
            sender,
            msg_context
        )
        return
        

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
                {"body": f"Enter total number of *Adults (Male)* age *more than 10 years*."},
                msg_context
            )
    elif active_session.get("adult_male") is None:
        if message_type == "text":
            value = payload.isnumeric()
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
            if value:
                value = int(payload)
                if value >= 0:
                    # Handle the validation logic for booking here
                    if (
                        active_session["adult_female"] <= 0
                        and active_session["child"] <= 0
                    ):
                        delete_booking_session(sender)
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
                        delete_booking_session(sender)
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

    # delete_booking_session(sender)
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


def send_booking_ticket(booking: Booking) -> str:
    """
    Function to send booking ticket to the user.

    :param `booking`: The booking instance
    :param `booking_id`: The booking id
    """
    try:
        booking_id = str(booking.id)
        pdf_path = generate_ticket_pdf(booking_id)
        if not USE_TEMPLATE_MESSAGE_BOOKING_TICKET:
            payload = {
                "link": pdf_path,
                "filename": f"{booking_id}.pdf",
                "caption": f"Your booking ticket is attached above for date: {booking.date.strftime("%a, %d %b %Y")}.",    
            }
            res = whatsapp_config.send_message(booking.wa_number, "document", payload)
        else:
            payload = {
                "name": "booking_ticket",
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "document",
                                "document": {
                                    "link": pdf_path,
                                    "filename": f"{booking_id}.pdf",
                                },
                            }
                        ],
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": booking.date.strftime("%a, %d %b %Y"),
                            }
                        ],
                    },
                ],
            }
            res = whatsapp_config.send_message(booking.wa_number, "template", payload)
        return f"Response: {res.json()}"
    except Exception as e:
        logging.exception(e)
        return f"Error: {str(e.args[0])}"


def send_my_bookings_message(sender: str, msg_context: dict|None=None):
    """
    Function to send my bookings message to the user.

    :param `sender`: The number to which message is to be sent
    :param `msg_context`: The context of the message i.e. for replying to msg
    """
    bookings = Booking.objects.filter(wa_number=sender, date__gte=timezone.now().date(), received_amount__gt=0).order_by("date")
    if bookings.exists():
        for booking in bookings:
            msg_str = f"Date: *{booking.date.strftime("%a, %d %b %Y")}*\nAdult (Male)): *{booking.adult_male}*\nAdult (Female): *{booking.adult_female}*\nChild: *{booking.child}*\nInfant: *{booking.infant}*\nTotal Amount: *{booking.total_amount} INR*\nAmount Paid: *{booking.received_amount} INR*\nAmount to be paid: *{booking.total_amount - booking.received_amount} INR*"
            payload = {
                "type": "button",
                "header": {
                    "type": "text",
                    "text": "Booking Details"
                },
                "body": {
                    "text": msg_str,
                },
                "action": {
                "buttons": [
                    {
                    "type": "reply",
                    "reply": {
                        "id": f"booking_ticket_{str(booking.id)}",
                        "title": "Get Ticket"
                    }
                    }
                ]
                }
            }
            
            res = whatsapp_config.send_message(sender, "interactive", payload, msg_context)
            logging.info(f"Response: {res.json()}")
    else:
        whatsapp_config.send_message(sender, "text", {"body": "No bookings found."}, msg_context)
    return        


def handle_sending_booking_ticket(sender: str, booking_id: str, msg_context: dict|None, booking: Booking|None=None):
    """
    Function to handle sending booking ticket to the user.

    :param `sender`: The number to which message is to be sent
    :param `booking_id`: The booking id
    :param `msg_context`: The context of the message i.e. for replying to msg
    :param `booking`: The booking instance
    """
    if not booking:
        booking = Booking.objects.filter(id=booking_id).first()
    if booking:
        res = send_booking_ticket(booking)
    else:
        res = whatsapp_config.send_message(sender, "text", {"body": "No booking found with given id."}, msg_context)
        res.json()
    return res


def handle_whatsapp_inquiry_message(sender: str) -> None:
    """
    Function to handle whatsapp inquiry message.

    :param `sender`: The number to which message is to be sent
    """
    inquiry_message = WhatsAppInquiryMessage.objects.all()
    res = []
    for msg in inquiry_message:
        if msg.type == "text":
            re = whatsapp_config.send_message(sender, "text", {"preview_url": True, "body": msg.message_text})
            res.append(re)
        elif msg.type == "image_only":
            re = whatsapp_config.send_message(sender, "image", {"link": f"{HOST_URL}{msg.document.url}"})
            res.append(re)
        elif msg.type == "image_with_text":
            re = whatsapp_config.send_message(sender, "image", {"link": f"{HOST_URL}{msg.document.url}", "caption": msg.message_text})
            res.append(re)
    logging.info(f"re: {str(res)}")
    return [r.json() for r in res]
            
    
def send_review_message(recipient_number: str, review_url: str) -> None:
    """
    Function to send review message to the user.

    :param `recipient_number`: The number to which message is to be sent
    :param `review_url`: The review url
    """
    payload = {
        "preview_url": True,
        "body": f"Please rate your experience with us.\n{review_url}",
    }
    whatsapp_config.send_message(recipient_number, "text", payload)

def send_daily_review_message():
    """
    Function to send daily review message to the user.
    """
    bookings = Booking.objects.filter(date=timezone.now().date(), received_amount__gt=0)
    review_url = os.environ.get("GOOGLE_REVIEW_LINK", "https://maps.app.goo.gl/KvjuDHHtCr6ZJFsu7")
    queue = django_rq.get_queue("low")
    if bookings.exists():
        for booking in bookings:
            queue.enqueue(send_review_message, booking.wa_number, review_url)
