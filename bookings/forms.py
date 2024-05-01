from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Submit
from crispy_forms.bootstrap import AccordionGroup, InlineRadios
from crispy_bootstrap5.bootstrap5 import FloatingField, BS5Accordion

from common_config.common import PAYMENT_FOR, PAYMENT_MODES_FORM
from .utils import add_payment_to_booking, create_or_update_booking
from .models import Booking
from management_core.models import Costume, TicketPrice


class BookingForm(forms.Form):
    wa_number = forms.CharField(max_length=10, label="WhatsApp Number", required=True)
    adult = forms.IntegerField(
        min_value=1,
        required=True,
        label="Adults",
        validators=[MinValueValidator(1, "At least 1 adult required")],
        initial=1,
    )
    child = forms.IntegerField(min_value=0, required=True, label="Children", initial=0)
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
        self.helper.add_layout(
            Layout(
                FloatingField("wa_number", pattern=r"^\d{10}$"),
                FloatingField("adult", min=1, css_class="w-50"),
                FloatingField("child", min=0, css_class="w-50"),
                FloatingField("date", css_class="w-50"),
                BS5Accordion(
                    AccordionGroup(
                        "Costumes",
                        *self.costume_sizes,
                        css_id="costume-accordion",
                    ),
                    always_open=False,
                    flush=False,
                ),
                BS5Accordion(
                    AccordionGroup(
                        "Special Booking",
                        "is_discounted_booking",
                        "special_ticket_total_amount",
                        "special_costume_total_amount",
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
            self.fields[size] = forms.IntegerField(
                min_value=0,
                required=False,
                label=size,
                initial=0,
            )

    def save(
        self, edit_booking: bool = False, booking_id: str | None = None
    ) -> Booking | bool:
        try:
            data = self.cleaned_data
            booking_data = {
                "wa_number": self.cleaned_data["wa_number"],
                "adult": self.cleaned_data["adult"],
                "child": self.cleaned_data["child"],
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
                FloatingField("payment_amount", css_class="w-50"),
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
