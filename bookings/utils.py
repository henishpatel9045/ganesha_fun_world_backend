from django.core.cache import cache
from datetime import datetime
from django.db import transaction
from django.shortcuts import get_object_or_404
import logging

from common_config.common import COSTUME_CACHE_KEY
from .models import Booking, BookingCostume, Payment, BookingCanteen
from management_core.models import TicketPrice, Costume


logging.getLogger(__name__)


def create_booking(
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
            booking = Booking(
                wa_number=wa_number,
                date=date,
                adult=adult,
                child=child,
                ticket_amount=(
                    special_ticket_total_amount
                    if is_discounted_booking
                    else ticket_total
                ),
                costume_amount=(
                    special_costume_total_amount
                    if is_discounted_booking
                    else costume_total
                ),
                total_amount=(
                    special_ticket_total_amount + special_costume_total_amount
                    if is_discounted_booking
                    else ticket_total + costume_total
                ),
                received_amount=received_amount,
                is_discounted_booking=is_discounted_booking,
                booking_type=booking_type,
            )
            booking.save()

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
            print()
            BookingCanteen(
                booking=booking,
            ).save()

            return booking
    except Exception as e:
        logging.exception(e)
        raise e
