from typing import Any
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.views.generic import FormView

from bookings.models import Booking
from .forms import BookingForm, PaymentRecordForm


class BookingFormView(FormView):
    template_name = "booking/booking.html"
    form_class = BookingForm

    def form_valid(self, form):
        try:
            booking = form.save()
            self.booking = booking
            return super().form_valid(form)
        except Exception as e:
            return super().form_invalid(form)

    def get_success_url(self) -> str:
        return f"/bookings/booking/{self.booking.id}/payment"


class PaymentFormView(FormView):
    template_name = "booking/payment.html"
    form_class = PaymentRecordForm

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        booking_id = kwargs.get("booking_id")
        if not booking_id:
            return HttpResponse("Booking ID is required")
        booking = Booking.objects.filter(id=booking_id).exists()
        if not booking:
            return HttpResponse("Booking not found")
        booking = Booking.objects.prefetch_related(
            "booking_costume", "booking_costume__costume"
        ).get(id=booking_id)
        costumes = booking.booking_costume.all
        form = PaymentRecordForm(
            initial={
                "booking": booking,
                "payment_amount": booking.total_amount - booking.received_amount,
            }
        )
        context = {
            "form": form,
            "booking": booking,
            "amount_to_collect": booking.total_amount - booking.received_amount,
            "costumes": costumes,
        }

        return render(request, "booking/payment.html", context=context)

    def form_valid(self, form):
        try:
            form.save()
            return super().form_valid(form)
        except Exception as e:
            return super().form_invalid(form)

    def get_success_url(self) -> str:
        return "/admin"
