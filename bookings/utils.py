from datetime import datetime, timedelta
from decimal import Decimal
import os
from django.db import transaction
from django.utils import timezone
import razorpay
import logging

from .models import Booking, BookingCostume, Payment, BookingCanteen
from management_core.models import TicketPrice, Costume

logging.getLogger(__name__)
razorpay_client = razorpay.Client(
    auth=(
        os.environ.get(
            "RAZORPAY_API_KEY",
        ),
        os.environ.get(
            "RAZORPAY_API_SECRET",
        ),
    ),
)
razorpay_client.set_app_details(
    {"title": "Ganesha WhatsApp Booking App", "version": "1.0.0"}
)


def create_or_update_booking(
    wa_number: str,
    date: datetime.date,
    adult_male: int,
    adult_female: int,
    child: int,
    booking_type: str,
    infant: int = 0,
    booking_costume_data: dict = {},
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
        adult_male (int): number of adult male persons
        adult_female (int): number of adult female persons
        child (int): number of child persons
        booking_costume_data (dict): dictionary of costume data in the format `{costume_name: quantity}`
        booking_type (str): type of the booking refer `BOOKING_TYPES` in `common_config` folder
        received_amount (float | str): amount received from the customer
        is_discounted_booking (bool): True if the booking is discounted and
    """
    try:
        # Add 91 to the number if it is 10 digit number
        if len(wa_number.strip()) == 10:
            wa_number = f"91{wa_number}"
        logging.info(
            "Create booking with data: ",
            {
                "wa_number": wa_number,
                "date": date,
                "adult_male": adult_male,
                "adult_female": adult_female,
                "child": child,
                "infant": infant,
                "booking_costume_data": booking_costume_data,
                "booking_type": booking_type,
                "received_amount": received_amount,
                "is_discounted_booking": is_discounted_booking,
                "special_ticket_total_amount": special_ticket_total_amount,
                "special_costume_total_amount": special_costume_total_amount,
            },
        )

        # Get pricelist data for the date of booking
        price_list = TicketPrice.objects.get(date=date)

        # Get costume data from DB for the costumes in the booking
        booking_costume_keys = booking_costume_data.keys()
        costume_price_list = Costume.objects.filter(name__in=booking_costume_keys)

        # Calculate the amount for the booking
        adult_price = price_list.adult * (adult_male + adult_female)
        child_price = price_list.child * child
        # TODO - Add other charges fields and logic

        # Create costume data to create BookingCostume objects
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
            # Create OR Update booking object
            if edit_booking:
                booking = existing_booking
            else:
                booking = Booking()
            booking.wa_number = wa_number
            booking.date = date
            booking.adult_male = adult_male
            booking.adult_female = adult_female
            booking.child = child
            booking.infant = infant
            booking.ticket_amount = (
                special_ticket_total_amount if is_discounted_booking else ticket_total
            )
            booking.costume_received_amount = (
                special_costume_total_amount
                if is_discounted_booking and special_costume_total_amount > 0
                else costume_total
            )
            booking.total_amount = (
                booking.ticket_amount
                + booking.costume_received_amount
                + booking.locker_received_amount
            )
            booking.received_amount = received_amount
            booking.is_discounted_booking = is_discounted_booking
            booking.booking_type = booking_type
            booking.save()

            # Delete existing booking costume data if it is an edit booking
            booking.booking_costume.all().delete()

            # Create BookingCostume objects
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

            # Create BookingCanteen object only if it is new booking.
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


def create_razorpay_order(amount, wa_number: str, booking: Booking):
    """Method to create razorpay order and return the order_id

    :param amount: amount to be paid
    :param note_data: dictionary of notes to be added to the order

    :return: payment link
    """
    amount = int(float(amount) * 100)
    note_data = {
        "booking_id": str(booking.id),
        "wa_number": str(booking.wa_number),
        "amount": str(booking.total_amount),
        "received_amount": str(booking.received_amount),
        "adult_male": str(booking.adult_male),
        "adult_female": str(booking.adult_female),
        "child": str(booking.child),
    }
    expire_time = timezone.now() + timedelta(minutes=16)
    expire_time = int(expire_time.timestamp())
    order = razorpay_client.payment_link.create(
        {
            "amount": amount,
            "currency": "INR",
            "accept_partial": False,
            "description": f"For Shree Ganesha Fun World Booking App with \nPhone: +{booking.wa_number}, \nDate: {booking.date.strftime('%d-%m-%Y')}, \nAdult (Male): {booking.adult_male}, \nAdult (Female): {booking.adult_female}, \nChild: {booking.child}",
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": note_data,
            "expire_by": expire_time,
            # "callback_url": f"https://leading-blindly-seahorse.ngrok-free.app/bookings/razorpay/webhook/?amount={amount}&booking_id={str(booking.id)}",  # TODO change this callback url after setting up the webhook
            # "callback_method": "get",
        }
    )
    return order
