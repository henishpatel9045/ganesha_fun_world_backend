from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Submit
from crispy_forms.bootstrap import AccordionGroup
from crispy_bootstrap5.bootstrap5 import FloatingField, BS5Accordion

from .utils import create_booking
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

    def save(self) -> Booking | bool:
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
            booking = create_booking(**booking_data)
            return booking
        except TicketPrice.DoesNotExist as e:
            self.add_error(None, f"TicketPrice details are not available for date {data['date']}")            
            raise forms.ValidationError()
        except Exception as e:
            self.add_error(None, e.args[0])
            raise forms.ValidationError()
