from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Submit
from crispy_forms.bootstrap import AccordionGroup
from crispy_bootstrap5.bootstrap5 import FloatingField, BS5Accordion


class BookingForm(forms.Form):
    wa_number = forms.CharField(max_length=10, label="WhatsApp Number", required=True)
    adult = forms.IntegerField(
        min_value=1,
        required=True,
        label="Adults",
        validators=[MinValueValidator(1, "At least 1 adult required")],
    )
    child = forms.IntegerField(
        min_value=0,
        required=True,
        label="Children",
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "value": timezone.now().date()}),
        required=True,
    )

    costume_sizes = ["small", "medium", "large"]

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
                    AccordionGroup("Costumes", *self.costume_sizes),
                    always_open=False,
                    flush=False,
                ),
                Submit("submit", "Save Booking", css_class="mt-3 btn-success"),
            )
        )

    def add_costume_fields(self):
        for size in self.costume_sizes:
            self.fields[f"{size}"] = forms.IntegerField(min_value=0, required=False)

    def save(self):
        print(self.data)
        return self.data
