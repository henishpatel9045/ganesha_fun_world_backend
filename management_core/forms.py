from datetime import timedelta
import os
from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from urllib.parse import quote
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Submit
from crispy_bootstrap5.bootstrap5 import FloatingField
import django_rq
import logging

from .models import Locker, TicketPrice, ExtraWhatsAppNumbers
from bookings.models import Booking
from whatsapp.messages.message_handlers import whatsapp_config
from common_config.common import (
    HOST_URL,
    TEMPORARY_FILE_LOCATION,
    GENERATED_MEDIA_BASE_URL,
)


logging.getLogger(__name__)
low_queue = django_rq.get_queue("low")


class TicketListPriceForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    adult = forms.DecimalField(decimal_places=2, max_digits=10)
    child = forms.DecimalField(decimal_places=2, max_digits=10)
    breakfast_price = forms.DecimalField(
        decimal_places=2, max_digits=10, required=False, initial=0.00
    )
    lunch_price = forms.DecimalField(
        decimal_places=2, max_digits=10, required=False, initial=0.00
    )
    dinner_price = forms.DecimalField(
        decimal_places=2, max_digits=10, required=False, initial=0.00
    )
    other_price = forms.DecimalField(
        decimal_places=2, max_digits=10, required=False, initial=0.00
    )
    other_price_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": "5"}),
        required=False,
        initial="",
    )

    def save(self):
        try:
            validated_data = self.cleaned_data
            # with transaction.atomic():
            for i in range(
                (validated_data["end_date"] - validated_data["start_date"]).days + 1
            ):
                date = validated_data["start_date"] + timedelta(days=i)
                try:
                    TicketPrice.objects.create(
                        date=date,
                        adult=validated_data["adult"],
                        child=validated_data["child"],
                        breakfast_price=validated_data["breakfast_price"],
                        lunch_price=validated_data["lunch_price"],
                        dinner_price=validated_data["dinner_price"],
                        other_price=validated_data["other_price"],
                        other_price_description=validated_data[
                            "other_price_description"
                        ],
                    )
                except Exception as e:
                    logging.exception(e)
                    self.add_error(
                        None,
                        "An error occurred while saving the data for date: "
                        + date.strftime("%Y-%m-%d"),
                    )
        except Exception as e:
            logging.exception(e)
            self.add_error(
                None, "An error occurred while saving the data: " + str(e.args[0])
            )


class LockerBulkAddForm(forms.Form):
    starting_number = forms.IntegerField()
    ending_number = forms.IntegerField()

    def save(self):
        try:
            validated_data = self.cleaned_data
            for i in range(
                validated_data["starting_number"], validated_data["ending_number"] + 1
            ):
                try:
                    Locker.objects.create(locker_number=i)
                except Exception as e:
                    logging.exception(e)
                    self.add_error(
                        None,
                        "An error occurred while saving the data for locker number: "
                        + str(i),
                    )
        except Exception as e:
            logging.exception(e)
            self.add_error(
                None, "An error occurred while saving the data: " + str(e.args[0])
            )


class TextOnlyPromotionalMessageForm(forms.Form):
    text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": "5"}),
        required=True,
        initial="",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            FloatingField("text"),
            Submit("submit", "Submit"),
        )

    def send_messages(self) -> None:
        try:
            msg_text = self.cleaned_data["text"]
            booking_phone_numbers = list(
                Booking.objects.all().values_list("wa_number", flat=True)
            )
            extra_phone_numbers = list(
                ExtraWhatsAppNumbers.objects.all().values_list("number", flat=True)
            )
            phone_numbers = set(booking_phone_numbers + extra_phone_numbers)

            for number in phone_numbers:
                try:
                    low_queue.enqueue(
                        whatsapp_config.send_message,
                        number,
                        "text",
                        {"preview_url": True, "body": msg_text},
                        None,
                    )
                except Exception as e:
                    logging.exception(e)
        except Exception as e:
            logging.exception(e)
            self.add_error(
                None, "An error occurred while sending the message: " + str(e.args[0])
            )


class ImageOnlyPromotionalMessageForm(forms.Form):
    image = forms.ImageField(
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            FloatingField("image"),
            Submit("submit", "Submit"),
        )

    def send_messages(self) -> None:
        try:
            image: InMemoryUploadedFile = self.cleaned_data["image"]
            image_path = f"{TEMPORARY_FILE_LOCATION}/promotional_images"
            os.makedirs(image_path, exist_ok=True)
            image_path = f"{image_path}/{image.name}"
            # save above file in the path
            with open(image_path, "wb") as f:
                for chunk in image.chunks():
                    f.write(chunk)

            hosted_image_path = (
                f"{HOST_URL}{GENERATED_MEDIA_BASE_URL}/promotional_images/{quote(image.name)}"
            )
            # Getting phone numbers from all the bookings so far and extra numbers from admin panel
            booking_phone_numbers = list(
                Booking.objects.all().values_list("wa_number", flat=True)
            )
            extra_phone_numbers = list(
                ExtraWhatsAppNumbers.objects.all().values_list("number", flat=True)
            )
            phone_numbers = set(booking_phone_numbers + extra_phone_numbers)

            for phone in phone_numbers:
                try:
                    low_queue.enqueue(
                        whatsapp_config.send_message,
                        phone,
                        "image",
                        {"link": hosted_image_path},
                        None,
                    )
                except Exception as e:
                    logging.exception(e)

        except Exception as e:
            logging.exception(e)
            self.add_error(
                None, "An error occurred while sending the message: " + str(e.args[0])
            )
