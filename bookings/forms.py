from typing import Any
from django import forms
from django.forms import formset_factory, BaseFormSet, modelformset_factory
from django.core.validators import MinValueValidator
from django.db import transaction
from django.utils import timezone
from django.db.models.query import QuerySet
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Submit, Row, Column
from crispy_forms.bootstrap import AccordionGroup, InlineRadios, Field
from crispy_bootstrap5.bootstrap5 import FloatingField, BS5Accordion
import django_rq

from common_config.common import PAYMENT_MODES_FORM
from whatsapp.messages.message_handlers import handle_sending_booking_ticket
from .utils import add_payment_to_booking, create_or_update_booking
from .models import Booking, BookingCanteen, BookingCostume, BookingLocker, Payment
from management_core.models import Costume, Locker, TicketPrice


high_queue = django_rq.get_queue("high")


## GATE MANAGEMENT FORMS
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
            if data["adult_female"] == 0 and data["child"] == 0:
                self.add_error(None, "At least one female or child is required.")
                raise Exception()
            if data["adult_female"] == 0 and data["adult_male"] == 0:
                self.add_error(None, "At least one adult is required.")
                raise Exception()
            if not edit_booking and self.cleaned_data["date"] != timezone.localtime(timezone.now()).date():
                self.add_error(None, "Booking is allowed only for today.")
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
            booking: Booking = self.cleaned_data["booking"]
            add_payment_to_booking(
                booking=self.cleaned_data["booking"],
                amount=self.cleaned_data["payment_amount"],
                payment_for="booking",
                payment_mode=self.cleaned_data["payment_mode"],
            )
            high_queue.enqueue(
                handle_sending_booking_ticket,
                booking.wa_number,
                "",
                None,
                booking,
                True
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
                if payment.payment_for != "booking":
                    return self.cleaned_data["booking"]

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

                high_queue.enqueue(
                    handle_sending_booking_ticket,
                    payment.booking.wa_number,
                    "",
                    None,
                    payment.booking,
                )
            return payment.booking
        except Exception as e:
            self.add_error(None, e.args[0])
            raise forms.ValidationError("")


## COSTUME MANAGEMENT FORMS
class CostumeReturnEditForm(forms.Form):
    id = forms.ModelChoiceField(
        queryset=BookingCostume.objects.prefetch_related("booking").all(),
        label="Booking Costume",
        required=False,
        widget=forms.Select(
            attrs={
                "id": "booking_costume_id",
                "readonly": "readonly",
            }
        ),
    )
    name = forms.CharField(
        label="Costume Name",
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "costume_name",
                "readonly": "readonly",
                "class": "title-field text-center w-100",
            }
        ),
    )
    issued_quantity = forms.IntegerField(
        initial=0,
        label="Issued Quantity",
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "id": "issued_quantity",
                "readonly": "readonly",
                "class": "readonly-field text-center w-100",
            }
        ),
    )
    returned_quantity = forms.IntegerField(
        initial=0,
        label="Returned Quantity",
        required=True,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "id": "returned_quantity",
                "class": "text-center w-100 form-control form-control-sm",
                "min": 0,
            }
        ),
    )
    returned_amount = forms.DecimalField(
        initial=0.00,
        label="Returned Amount",
        required=True,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "id": "returned_amount",
                "class": "text-center w-100 form-control form-control-sm",
                "min": 0,
            }
        ),
    )

    def save(self):
        try:
            booking_costume: BookingCostume = self.cleaned_data["id"]

            previous_returned_amount = booking_costume.returned_amount

            booking_costume.returned_quantity = self.cleaned_data["returned_quantity"]
            booking_costume.returned_at = timezone.localtime(timezone.now())
            if booking_costume.returned_quantity > booking_costume.issued_quantity:
                raise forms.ValidationError(
                    "Returned quantity can't be more than issued quantity."
                )
            booking_costume.returned_amount = self.cleaned_data["returned_amount"]
            if booking_costume.returned_amount > booking_costume.deposit_amount:
                raise forms.ValidationError(
                    "Returned amount can't be more than deposit amount."
                )

            booking_costume.save()
            return booking_costume, previous_returned_amount
        except Exception as e:
            self.add_error(None, e.args[0])
            raise forms.ValidationError("")


BookingCostumeFormSet = formset_factory(CostumeReturnEditForm, extra=0)


## BOUNCER FORMS
class BouncerCheckInForm(forms.Form):
    checked_in = forms.IntegerField(initial=0, required=True, min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.add_layout(
            Layout(
                FloatingField("checked_in", css_class="w-100"),
                Submit("submit", "Save Check In", css_class="mt-3 btn-success"),
            )
        )

    def save(self, booking: Booking):
        try:
            if int(self.cleaned_data["checked_in"]) > booking.total_persons():
                raise Exception(f"Checked in people can't be more than total people.")
            booking.total_checked_in = self.cleaned_data["checked_in"]
            booking.save()
            return booking
        except Exception as e:
            self.add_error(None, e.args[0])
            raise forms.ValidationError("")


## CANTEEN MANAGEMENT FORMS
class CanteenCardForm(forms.Form):
    breakfast_currently_used = forms.IntegerField(
        initial=0,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "id": "breakfast_currently_used",
                "class": "readonly-field py-2 text-center w-100",
            }
        ),
    )
    lunch_currently_used = forms.IntegerField(
        initial=0,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "id": "lunch_currently_used",
                "class": "readonly-field py-2 text-center w-100",
            }
        ),
    )
    evening_snacks_currently_used = forms.IntegerField(
        initial=0,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "id": "evening_snacks_currently_used",
                "class": "readonly-field py-2 text-center w-100",
            }
        ),
    )

    def save(self, canteen_card: BookingCanteen):
        try:
            canteen_card.breakfast_quantity_used += int(
                self.cleaned_data["breakfast_currently_used"]
            )
            canteen_card.lunch_quantity_used += int(
                self.cleaned_data["lunch_currently_used"]
            )
            canteen_card.evening_snacks_quantity_used += int(
                self.cleaned_data["evening_snacks_currently_used"]
            )
            canteen_card.save()
        except Exception as e:
            self.add_error(None, e.args[0])
            raise forms.ValidationError("")


class LockerAddForm(forms.ModelForm):
    locker = forms.ModelChoiceField(
        queryset=Locker.objects.filter(is_available=True),
        label="Locker",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = BookingLocker
        fields = [
            "locker",
            "deposit_amount",
        ]
        widgets = {
            "deposit_amount": forms.NumberInput(
                attrs={
                    "class": "form-control text-center",
                    "min": 0,
                }
            ),
        }

    def save(self, booking: Booking, commit: bool = ...) -> Any:
        try:
            self.instance.booking = booking
            self.instance.locker.is_available = False
            self.instance.save()
            self.instance.locker.save()
            return super().save(commit)
        except Exception as e:
            self.add_error("locker", e.args[0])
            raise forms.ValidationError("")


class LockerBaseFormSet(BaseFormSet):
    def clean(self) -> None:
        if any(self.errors):
            return
        lockers = set(form.cleaned_data.get("locker") for form in self.forms)

        if len(lockers) != len(self.forms):
            raise forms.ValidationError("Duplicate locker selected.")


def get_locker_add_formset(locker_count: int) -> Any:
    LockerAddFormSet = formset_factory(
        LockerAddForm, extra=locker_count, formset=LockerBaseFormSet
    )
    return LockerAddFormSet


class LockerEditForm(forms.ModelForm):
    locker = forms.ModelChoiceField(
        queryset=Locker.objects.filter(is_available=True),
        label="Locker",
        required=True,
        widget=forms.Select(attrs={"class": "form-control text-center"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locker_instance_list = [self.instance]
        # Create a queryset from the list
        locker_instance_qs = QuerySet(
            model=Locker,
            query=Locker.objects.filter(pk=self.instance.locker.pk).query.clone(),
        )
        locker_instance_qs._result_cache = locker_instance_list
        self.fields["locker"].queryset = locker_instance_qs | Locker.objects.filter(
            is_available=True
        )

    class Meta:
        model = BookingLocker
        fields = [
            "id",
            "locker",
            "deposit_amount",
        ]
        widgets = {
            "deposit_amount": forms.NumberInput(
                attrs={
                    "class": "form-control text-center readonly-field",
                    "min": 0,
                }
            ),
        }


class LockerReturnForm(forms.ModelForm):
    locker = forms.ModelChoiceField(
        queryset=Locker.objects.filter(is_available=True),
        label="Locker",
        required=True,
        widget=forms.Select(
            attrs={"class": "form-control text-center", "readonly": "readonly"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locker_instance_list = [self.instance]
        # Create a queryset from the list
        locker_instance_qs = QuerySet(
            model=Locker,
            query=Locker.objects.filter(pk=self.instance.locker.pk).query.clone(),
        )
        locker_instance_qs._result_cache = locker_instance_list
        self.fields["locker"].queryset = locker_instance_qs

    class Meta:
        model = BookingLocker
        fields = [
            "id",
            "locker",
            "deposit_amount",
            "returned_amount",
            "is_returned",
        ]
        widgets = {
            "deposit_amount": forms.NumberInput(
                attrs={
                    "class": "form-control text-center readonly-field",
                    "min": 0,
                    "readonly": "readonly",
                }
            ),
            "returned_amount": forms.NumberInput(
                attrs={
                    "class": "form-control text-center",
                    "min": 0,
                }
            ),
            "is_returned": forms.CheckboxInput(
                attrs={"class": "form-control form-check-input"}
            ),
        }

    def save(self, commit: bool = ...) -> Any:
        locker: BookingLocker = super().save(commit)
        locker.locker.is_available = True
        locker.locker.save()
        return locker


LockerEditFormSet = modelformset_factory(BookingLocker, form=LockerEditForm, extra=0)

LockerReturnFormSet = modelformset_factory(
    BookingLocker, form=LockerReturnForm, extra=0
)
