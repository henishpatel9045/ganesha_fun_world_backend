from datetime import timedelta
from django import forms
from django.db import transaction
import logging

from .models import TicketPrice


logging.getLogger(__name__)


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
