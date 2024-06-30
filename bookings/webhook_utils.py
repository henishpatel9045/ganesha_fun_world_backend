from django.db import transaction
from decimal import Decimal
import django_rq
import logging

from bookings.models import Booking, Payment
from common_config.common import ADVANCE_PER_PERSON_AMOUNT_FOR_BOOKING
from whatsapp.messages.message_handlers import handle_sending_booking_ticket

logging.getLogger(__name__)


def handle_razorpay_webhook_booking_payment(data: dict) -> bool:
    try:
        # TODO uncomment below lines after implementing the razorpay payment gateway webhook
        payment_payload = data["payload"]["payment"]["entity"]
        status = payment_payload["status"]
        received_amount = payment_payload["amount"]
        notes = payment_payload["notes"]

        if status != "captured":
            raise Exception("Payment not captured")
        booking_id = notes.get("booking_id")
        if not booking_id:
            raise Exception("Booking ID not found in notes")
        received_amount = received_amount / 100

        booking = Booking.objects.get(id=booking_id)
        
        if booking.received_amount > 0:
            logging.warning(f"Booking already paid and updated for booking_id: {booking_id}")
            return True
        
        # FIXME currently we are just taking advanced payment only, for the booking
        total_persons = booking.adult_male + booking.adult_female + booking.child
        total_amount = total_persons * ADVANCE_PER_PERSON_AMOUNT_FOR_BOOKING

        if total_amount != received_amount:
            raise Exception("Amount mismatched")

        with transaction.atomic():
            payment = Payment()
            payment.booking = booking
            payment.payment_mode = "payment_gateway"
            payment.payment_for = "booking"
            payment.amount = received_amount
            payment.is_confirmed = True
            payment.payment_data = data
            payment.booking.received_amount += Decimal(payment.amount)
            payment.booking.save()
            payment.save()
        django_rq.enqueue(
            handle_sending_booking_ticket,
            booking.wa_number,
            "",
            None,
            booking,
            True
        )
        return True
    except Exception as e:
        logging.error(f"Razorpay ReqData: {str(data)}")
        logging.exception(e)
        return False
