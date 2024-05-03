import uuid
from django.db import models, transaction
from django.core.validators import MinValueValidator
from django.utils import timezone

from common_config.common import BOOKING_TYPES, PAYMENT_FOR, PAYMENT_MODES


class DateTimeBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Booking(DateTimeBaseModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True
    )
    wa_number = models.CharField(max_length=15, db_index=True, null=False)
    adult_male = models.PositiveIntegerField(default=0)
    adult_female = models.PositiveIntegerField(default=0)
    child = models.PositiveIntegerField(default=0)
    infant = models.PositiveIntegerField(default=0)
    booking_type = models.CharField(
        max_length=50, choices=BOOKING_TYPES, default=BOOKING_TYPES[0][0]
    )
    date = models.DateField(null=True, blank=True)
    ticket_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    costume_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    # TODO - Add other charges fields
    total_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    received_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    is_discounted_booking = models.BooleanField(default=False)

    def total_persons(self):
        """Returns total number of persons in the booking"""
        return self.adult_male + self.adult_female + self.child

    def is_active(self):
        """Returns True if the booking is active currently i.e. the date is today."""
        return self.date == timezone.datetime.today().date()

    def __str__(self) -> str:
        return f"{self.wa_number} - {self.date.strftime('%d-%m-%Y')}"


class Payment(DateTimeBaseModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True
    )
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, db_index=True, related_name="booking_payment"
    )
    payment_mode = models.CharField(
        max_length=50, choices=PAYMENT_MODES, default=PAYMENT_MODES[0][0]
    )
    payment_for = models.CharField(
        max_length=50, choices=PAYMENT_FOR, default=PAYMENT_FOR[0][0]
    )
    amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    payment_data = models.JSONField(null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)
    is_returned_to_customer = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.booking.wa_number} - {self.amount} - {self.payment_mode} - {self.payment_for}"

    def delete(self, *args, **kwargs):
        """Override delete method to update the booking received amount."""
        with transaction.atomic():
            if self.booking:
                booking = self.booking
                booking.received_amount -= self.amount
                booking.save()
            return super().delete(*args, **kwargs)


class BookingCostume(DateTimeBaseModel):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, db_index=True, related_name="booking_costume"
    )
    costume = models.ForeignKey(
        "management_core.Costume", on_delete=models.DO_NOTHING, db_index=True
    )
    quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(1)])
    deposit_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_quantity = models.PositiveIntegerField(default=0)
    returned_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)

    def __str__(self) -> str:
        return f"{self.booking.wa_number} - {self.costume.name} - {self.quantity}"


class BookingLocker(DateTimeBaseModel):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, db_index=True, related_name="booking_locker"
    )
    locker = models.ForeignKey(
        "management_core.Locker", on_delete=models.DO_NOTHING, db_index=True
    )
    deposit_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)

    def __str__(self) -> str:
        return f"{self.booking.wa_number} - {self.locker.name}"


class BookingCanteen(DateTimeBaseModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True
    )
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, db_index=True, related_name="booking_canteen"
    )
    breakfast_quantity_used = models.PositiveIntegerField(default=0)
    lunch_quantity_used = models.PositiveIntegerField(default=0)
    evening_snacks_quantity_used = models.PositiveIntegerField(default=0)
    dinner_quantity_used = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.booking.wa_number} - {self.breakfast_quantity_used} - {self.lunch_quantity_used} - {self.evening_snacks_quantity_used} - {self.dinner_quantity_used}"
