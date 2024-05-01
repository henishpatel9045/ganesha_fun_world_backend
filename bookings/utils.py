from django.core.cache import cache
from datetime import datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
import logging

from common_config.common import COSTUME_CACHE_KEY
from .models import Booking, BookingCostume, Payment, BookingCanteen
from management_core.models import TicketPrice, Costume


logging.getLogger(__name__)


def create_or_update_booking(
    wa_number: str,
    date: datetime.date,
    adult: int,
    child: int,
    booking_costume_data: dict,
    booking_type: str,
    is_discounted_booking: bool = False,
    special_ticket_total_amount=None,
    special_costume_total_amount=None,
    received_amount: float | str = 0,
    edit_booking: bool = False,
    existing_booking: Booking | None = None,
):
    """Method to create booking with costumes and canteen items.
    Calculate amount using management_core models -> Create Booking -> Create BookingCostume -> Create BookingCanteen

    Args:
        wa_number (str): whatsapp number of the customer
        date (datetime.date): date of the booking (i.e. date of the event)
        adult (int): number of adult persons
        child (int): number of child persons
        booking_costume_data (dict): dictionary of costume data in the format `{costume_name: quantity}`
        booking_type (str): type of the booking refer `BOOKING_TYPES` in `common_config` folder
        received_amount (float | str): amount received from the customer
        is_discounted_booking (bool): True if the booking is discounted and
    """
    try:
        logging.info(
            "Create booking with data: ",
            {
                "wa_number": wa_number,
                "date": date,
                "adult": adult,
                "child": child,
                "booking_costume_data": booking_costume_data,
                "booking_type": booking_type,
                "received_amount": received_amount,
                "is_discounted_booking": is_discounted_booking,
                "special_ticket_total_amount": special_ticket_total_amount,
                "special_costume_total_amount": special_costume_total_amount,
            },
        )

        price_list = TicketPrice.objects.get(date=date)
        booking_costume_keys = booking_costume_data.keys()
        costume_price_list = Costume.objects.filter(name__in=booking_costume_keys)

        adult_price = price_list.adult * adult
        child_price = price_list.child * child
        # TODO - Add other charges fields and logic
        costume_data = []
        for costume in costume_price_list:
            costume_data.append(
                (
                    costume,
                    booking_costume_data[costume.name],
                    costume.price * booking_costume_data[costume.name],
                )
            )

        ticket_total = adult_price + child_price
        costume_total = sum([costume[2] for costume in costume_data])

        with transaction.atomic():
            if edit_booking:
                booking = existing_booking
            else:
                booking = Booking()
            booking.wa_number = wa_number
            booking.date = date
            booking.adult = adult
            booking.child = child
            booking.ticket_amount = (
                special_ticket_total_amount if is_discounted_booking else ticket_total
            )
            booking.costume_amount = (
                special_costume_total_amount if is_discounted_booking else costume_total
            )
            booking.total_amount = (
                special_ticket_total_amount + special_costume_total_amount
                if is_discounted_booking
                else ticket_total + costume_total
            )
            booking.received_amount = received_amount
            booking.is_discounted_booking = is_discounted_booking
            booking.booking_type = booking_type
            booking.save()

            booking.booking_costume.all().delete()
            
            issued_costumes = []
            for costume in costume_data:
                issued_costumes.append(
                    BookingCostume(
                        booking=booking,
                        costume=costume[0],
                        quantity=costume[1],
                        deposit_amount=costume[0].price * costume[1],
                    )
                )
            BookingCostume.objects.bulk_create(issued_costumes)
            if not edit_booking:
                BookingCanteen(
                    booking=booking,
                ).save()

            return booking
    except Exception as e:
        logging.exception(e)
        raise e


def add_payment_to_booking(
    booking: Booking,
    amount: float | str,
    payment_for: str,
    payment_mode: str,
    is_confirmed: bool = True,
    is_returned_to_customer: bool = False,
):
    """Method to add payment to the booking

    Args:
        booking (Booking): Booking object
        amount (float | str): amount received from the customer
        payment_for (str): purpose of the payment refer `PAYMENT_FOR` in `common_config` folder
        payment_mode (str): mode of the payment refer `PAYMENT_MODES` in `common_config` folder
        is_confirmed (bool): True if the payment is confirmed
        is_returned_to_customer (bool): True if the payment is returned to the customer
    """
    try:
        logging.info(
            "Add payment to booking with data: ",
            {
                "booking": booking,
                "amount": amount,
                "payment_for": payment_for,
                "payment_mode": payment_mode,
                "is_confirmed": is_confirmed,
                "is_returned_to_customer": is_returned_to_customer,
            },
        )

        if booking.total_amount < booking.received_amount + amount:
            raise ValueError("Amount exceeds the total amount of the booking")

        payment = Payment(
            booking=booking,
            amount=amount,
            payment_for=payment_for,
            payment_mode=payment_mode,
            is_confirmed=is_confirmed,
            is_returned_to_customer=is_returned_to_customer,
        )
        with transaction.atomic():
            booking.received_amount += amount
            payment.save()
            booking.save()
            return payment
    except Exception as e:
        logging.exception(e)
        raise e
