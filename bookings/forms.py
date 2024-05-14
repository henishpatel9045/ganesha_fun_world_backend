from typing import Any
from django import forms
from django.core.validators import MinValueValidator
from django.db import transaction
from django.utils import timezone
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Submit, Row, Column
from crispy_forms.bootstrap import AccordionGroup, InlineRadios, Field
from crispy_bootstrap5.bootstrap5 import FloatingField, BS5Accordion

from common_config.common import PAYMENT_MODES_FORM
from .utils import add_payment_to_booking, create_or_update_booking
from .models import Booking, Payment
from management_core.models import Costume, TicketPrice


class BookingForm(forms.Form):
    wa_number = forms.CharField(
        max_length=12,
        label="WhatsApp Number",
        required=True,
    )
    adult_male = forms.IntegerField(
        min_value=0,
        required=True,
        label="Adults (Male)",
        validators=[MinValueValidator(0, "Value can't be negative.")],
        initial=0,
    )
    adult_female = forms.IntegerField(
        min_value=0,
        required=True,
        label="Adults (Female)",
        validators=[MinValueValidator(0, "Value can't be negative.")],
        initial=0,
    )
    child = forms.IntegerField(
        min_value=0, required=True, label="Children (5 - 10 years)", initial=0
    )
    infant = forms.IntegerField(min_value=0, label="Infants (0 - 5 years)", initial=0)
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "value": timezone.now().date()}),
        required=True,
    )
    is_discounted_booking = forms.BooleanField(
        required=False,
        label="Discounted Booking",
        initial=False,
        widget=forms.CheckboxInput(attrs={"id": "is_discounted_booking"}),
    )
    special_ticket_total_amount = forms.DecimalField(
        required=False,
        label="Special Ticket Total Amount",
        initial=0,
        widget=forms.NumberInput(attrs={"id": "special_ticket_total_amount"}),
    )
    special_costume_total_amount = forms.DecimalField(
        required=False,
        label="Special Costume Total Amount",
        initial=0,
        widget=forms.NumberInput(attrs={"id": "special_costume_total_amount"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_costume_fields()
        self.helper = FormHelper()
        costume_fields = [
            FloatingField(size, min=0, css_class="w-100") for size in self.costume_sizes
        ]
        self.helper.add_layout(
            Layout(
                Row(
                    Column(
                        FloatingField(
                            "wa_number", pattern=r"^\d{10}$|^\d{12}$", max_length=12
                        ),
                    ),
                    Column(FloatingField("date", css_class="w-100")),
                ),
                Row(
                    Column(
                        FloatingField(
                            "adult_male",
                            min=0,
                            css_class="w-100",
                        ),
                    ),
                    Column(
                        FloatingField("adult_female", min=0, css_class="w-100"),
                    ),
                ),
                Row(
                    Column(
                        FloatingField("child", min=0, css_class="w-100"),
                    ),
                    Column(
                        FloatingField("infant", css_class="w-100"),
                    ),
                ),
                BS5Accordion(
                    AccordionGroup(
                        "Costumes",
                        *[
                            Row(
                                *[
                                    Column(field)
                                    for field in costume_fields[index : index + 2]
                                ]
                            )
                            for index in range(0, len(costume_fields), 2)
                        ],
                        css_id="costume-accordion",
                    ),
                    always_open=False,
                    # flush=False,
                ),
                BS5Accordion(
                    AccordionGroup(
                        "Special Booking",
                        "is_discounted_booking",
                        FloatingField("special_ticket_total_amount"),
                        FloatingField("special_costume_total_amount"),
                        css_id="special-booking-accordion",
                    )
                ),
                Submit("submit", "Save Booking", css_class="mt-3 btn-success"),
            )
        )

    def add_costume_fields(self) -> None:
        sizes = Costume.objects.filter(is_available=True).values_list("name", flat=True)
        self.costume_sizes = sizes
        for size in sizes:
            self.fields[size.replace(" ", "_")] = forms.IntegerField(
                min_value=0,
                required=False,
                label=size,
                initial=0,
            )

    def clean_wa_number(self) -> str:
        self.cleaned_data["wa_number"] = self.cleaned_data["wa_number"].replace(" ", "")
        if len(self.cleaned_data["wa_number"]) == 10:
            self.cleaned_data["wa_number"] = "91" + self.cleaned_data["wa_number"]
        return self.cleaned_data["wa_number"]

    def save(
        self, edit_booking: bool = False, booking_id: str | None = None
    ) -> Booking | bool:
        try:
            data = self.cleaned_data
            print("Inside Save: ", data)
            if data["adult_female"] == 0 and data["child"] == 0:
                self.add_error(None, "At least one female or child is required.")
                raise Exception()
            if data["adult_female"] == 0 and data["adult_male"] == 0:
                self.add_error(None, "At least one adult is required.")
                raise Exception()
            booking_data = {
                "wa_number": self.cleaned_data["wa_number"],
                "adult_male": self.cleaned_data["adult_male"],
                "adult_female": self.cleaned_data["adult_female"],
                "child": self.cleaned_data["child"],
                "infant": self.cleaned_data["infant"],
                "date": self.cleaned_data["date"],
                "is_discounted_booking": self.cleaned_data["is_discounted_booking"],
                "special_ticket_total_amount": self.cleaned_data[
                    "special_ticket_total_amount"
                ],
                "special_costume_total_amount": self.cleaned_data[
                    "special_costume_total_amount"
                ],
                "booking_type": "gate_booking",
                "booking_costume_data": {
                    size: data[size] for size in self.costume_sizes if data[size] > 0
                },
            }
            if edit_booking:
                existing_booking = Booking.objects.get(id=booking_id)
                booking = create_or_update_booking(
                    **booking_data,
                    received_amount=existing_booking.received_amount,
                    edit_booking=edit_booking,
                    existing_booking=existing_booking,
                )
            else:
                booking = create_or_update_booking(**booking_data)
            return booking
        except TicketPrice.DoesNotExist as e:
            self.add_error(
                None, f"TicketPrice details are not available for date {data['date']}"
            )
            raise forms.ValidationError()
        except Exception as e:
            self.add_error(None, e.args[0])
            raise forms.ValidationError()


class PaymentRecordForm(forms.Form):
    booking = forms.ModelChoiceField(
        queryset=Booking.objects.all(),
        label="Booking",
        required=False,
        widget=forms.Select(
            attrs={
                "id": "payment_booking",
            }
        ),
    )
    payment_amount = forms.DecimalField(
        required=True,
        label="Payment Amount",
        widget=forms.NumberInput(attrs={"id": "payment_amount"}),
    )
    payment_mode = forms.ChoiceField(
        choices=PAYMENT_MODES_FORM,
        required=True,
        label="Payment Mode",
        widget=forms.RadioSelect(attrs={"id": "payment_mode"}),
        initial="gate_upi",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_layout(
            Layout(
                FloatingField("booking", css_class="w-50"),
                FloatingField("payment_amount", css_class="w-50", editable=False),
                InlineRadios("payment_mode", css_class="w-fit"),
                Submit(
                    "submit",
                    "Save Payment",
                    css_class="mt-3 btn-success",
                    css_id="payment_submit",
                ),
            )
        )

    def save(self) -> Booking:
        try:
            print(self.cleaned_data)
            add_payment_to_booking(
                booking=self.cleaned_data["booking"],
                amount=self.cleaned_data["payment_amount"],
                payment_for="booking",
                payment_mode=self.cleaned_data["payment_mode"],
            )
            return self.cleaned_data["booking"]
        except Exception as e:
            self.add_error(None, e.args[0])
            raise forms.ValidationError()


class PaymentRecordEditForm(forms.Form):
    booking = forms.ModelChoiceField(
        queryset=Booking.objects.all(),
        label="Booking",
        required=False,
        widget=forms.Select(
            attrs={
                "id": "payment_booking",
            }
        ),
    )
    payment_amount = forms.DecimalField(
        required=True,
        label="Payment Amount",
        widget=forms.NumberInput(attrs={"id": "payment_amount"}),
    )
    payment_mode = forms.ChoiceField(
        choices=PAYMENT_MODES_FORM,
        required=True,
        label="Payment Mode",
        widget=forms.RadioSelect(attrs={"id": "payment_mode"}),
        initial="gate_upi",
    )
    is_confirmed = forms.BooleanField(
        required=False,
        label="Payment Confirmed",
        widget=forms.CheckboxInput(attrs={"id": "is_confirmed"}),
    )
    is_returned_to_customer = forms.BooleanField(
        required=False,
        label="Returned to Customer",
        widget=forms.CheckboxInput(attrs={"id": "is_returned_to_customer"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_layout(
            Layout(
                FloatingField("booking", css_class="w-50"),
                FloatingField("payment_amount", css_class="w-50", editable=False),
                InlineRadios("payment_mode", css_class="w-fit"),
                Field("is_confirmed", css_class="w-fit"),
                Field("is_returned_to_customer", css_class="w-fit"),
                Submit(
                    "submit",
                    "Save Payment",
                    css_class="mt-3 btn-success",
                    css_id="payment_submit",
                ),
            )
        )

    def save(self, payment_id: str) -> Booking:
        try:
            with transaction.atomic():
                payment = Payment.objects.get(id=payment_id)
                payment.payment_mode = self.cleaned_data["payment_mode"]
                payment.is_confirmed = self.cleaned_data["is_confirmed"]

                # If payment is not returned to customer, then update booking received amount
                if (
                    not payment.is_returned_to_customer
                    and self.cleaned_data["is_returned_to_customer"]
                ):
                    payment.amount = self.cleaned_data["payment_amount"]
                    payment.booking.received_amount -= payment.amount

                elif (
                    payment.is_returned_to_customer
                    and not self.cleaned_data["is_returned_to_customer"]
                ):
                    payment.amount = self.cleaned_data["payment_amount"]
                    if (
                        payment.booking.received_amount + payment.amount
                        > payment.booking.total_amount
                    ):
                        self.add_error(None, "Payment amount exceeds total amount.")
                        raise forms.ValidationError("")
                    if payment.is_confirmed:
                        payment.booking.received_amount += payment.amount


                elif (
                    not payment.is_returned_to_customer
                    and not self.cleaned_data["is_returned_to_customer"]
                ):
                    payment.booking.received_amount -= payment.amount
                    payment.amount = self.cleaned_data["payment_amount"]
                    if (
                        payment.booking.received_amount + payment.amount
                        > payment.booking.total_amount
                    ):
                        self.add_error(None, "Payment amount exceeds total amount.")
                        raise forms.ValidationError("")
                    if payment.is_confirmed:
                        payment.booking.received_amount += payment.amount

                else:
                    payment.amount = self.cleaned_data["payment_amount"]

                payment.is_returned_to_customer = self.cleaned_data[
                    "is_returned_to_customer"
                ]
                payment.save()
                payment.booking.save()
            return self.cleaned_data["booking"]
        except Exception as e:
            self.add_error(None, e.args[0])
            raise forms.ValidationError("")
