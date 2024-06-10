from django.db import models

from common_config.common import WHATSAPP_INQUIRY_MSG_TYPES


class DateTimeBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-updated_at"]


class TicketPrice(DateTimeBaseModel):
    date = models.DateField(db_index=True, null=False, unique=True)
    adult = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    child = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    breakfast_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    lunch_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    dinner_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    other_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    other_price_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.date.strftime("%A, %d %B %Y")

    class Meta:
        ordering = ["-date"]


class Costume(DateTimeBaseModel):
    name = models.CharField(max_length=100, db_index=True, null=False)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Locker(DateTimeBaseModel):
    locker_number = models.CharField(
        max_length=100,
        db_index=True,
        null=False,
        unique=True,
    )
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.locker_number

    class Meta:
        ordering = ["locker_number"]


class WhatsAppInquiryMessage(DateTimeBaseModel):
    name = models.CharField(max_length=200, blank=True, null=True)
    type = models.CharField(
        max_length=50, choices=WHATSAPP_INQUIRY_MSG_TYPES, default="text", null=False
    )
    message_text = models.TextField(null=True, blank=True)
    document = models.FileField(null=True, blank=True, upload_to="whatsapp_inquiry")
    sent_order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.sent_order} - {self.type}"

    class Meta:
        ordering = ["sent_order"]


class ExtraWhatsAppNumbers(DateTimeBaseModel):
    number = models.CharField(max_length=20, blank=False, null=False, unique=True)

    def __str__(self) -> str:
        return self.number
