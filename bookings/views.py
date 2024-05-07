from typing import Any
from django.forms.forms import BaseForm
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.views.generic import FormView, TemplateView

from bookings.models import Booking
from management_core.models import TicketPrice
from .forms import BookingForm, PaymentRecordForm
from .utils import create_razorpay_order
from .ticket.utils import generate_booking_id_qrcode


class BookingHomeTemplateView(TemplateView):
    template_name = "booking/booking_home.html"


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


class BookingEditFormView(FormView):
    template_name = "booking/booking_edit.html"
    form_class = BookingForm

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        booking_id = kwargs.get("booking_id")
        if not booking_id:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking ID is required."},
            )
        booking = Booking.objects.filter(id=booking_id).exists()
        if not booking:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking not found."},
            )
        booking = Booking.objects.prefetch_related(
            "booking_costume", "booking_costume__costume"
        ).get(id=booking_id)
        costumes = booking.booking_costume.all()
        initial_data = {
            "wa_number": booking.wa_number,
            "adult_male": booking.adult_male,
            "adult_female": booking.adult_female,
            "child": booking.child,
            "date": booking.date,
            "is_discounted_booking": booking.is_discounted_booking,
            "special_ticket_total_amount": (
                booking.ticket_amount if booking.is_discounted_booking else 0
            ),
            "special_costume_total_amount": (
                booking.costume_amount if booking.is_discounted_booking else 0
            ),
            **{costume.costume.name: costume.quantity for costume in costumes},
        }

        form = BookingForm(initial=initial_data)
        return render(request, "booking/booking_edit.html", context={"form": form})

    def form_valid(self, form):
        try:
            booking = form.save(
                edit_booking=True, booking_id=self.kwargs.get("booking_id")
            )
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
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking ID is required."},
            )
        booking = Booking.objects.filter(id=booking_id).exists()
        if not booking:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking not found."},
            )
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
        return f"/bookings/booking/{self.kwargs.get('booking_id')}/summary"


class BookingSummaryCardTemplateView(TemplateView):
    def get_context_data(self, **kwargs):
        booking_id = kwargs.get("booking_id")
        if not booking_id:
            return False
        booking = Booking.objects.filter(id=booking_id).exists()
        if not booking:
            return False
        booking = Booking.objects.prefetch_related("booking_costume").get(id=booking_id)
        context = {
            "booking_id": booking.id,
            "wa_number": booking.wa_number,
            "booked_on": booking.created_at,
            "date": booking.date,
            "adult_male": booking.adult_male,
            "adult_female": booking.adult_female,
            "child": booking.child,
            "ticket_amount": booking.ticket_amount,
            "costume_amount": booking.costume_amount,
            "total_amount": booking.total_amount,
            "received_amount": booking.received_amount,
            "amount_to_collect": booking.total_amount - booking.received_amount,
        }
        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data(**kwargs)
        if not context:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking ID is required."},
            )
        return render(request, "booking/booking_summary_card.html", context=context)


class BookingTicketTemplateView(TemplateView):
    template_name = "booking/booking_ticket.html"

    def get_gst_amount(self, total, percentage):
        total, percentage = float(total), float(percentage)
        return round((total / (1 + percentage)) * percentage, 2)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        booking_id = kwargs.get("booking_id")
        if not booking_id:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking ID is required."},
            )
        booking = Booking.objects.filter(id=booking_id).exists()
        if not booking:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking not found."},
            )
        booking = Booking.objects.prefetch_related(
            "booking_costume", "booking_costume__costume"
        ).get(id=booking_id)
        price_list = TicketPrice.objects.filter(date=booking.date).first()
        costume_data = booking.booking_costume.all()
        print(costume_data)
        qr_code_url = generate_booking_id_qrcode(booking_id)
        context = {
            "qr_code_url": qr_code_url,
            "booking": booking,
            "adult_male_price": price_list.adult,
            "adult_female_price": price_list.adult,
            "adult_male_total": price_list.adult * booking.adult_male,
            "adult_female_total": price_list.adult * booking.adult_female,
            "child_total": price_list.child * booking.child,
            "child_price": price_list.child,
            "amount_to_collect": booking.total_amount - booking.received_amount,
            "costume_data": costume_data,
            "sgst_amount": self.get_gst_amount(booking.total_amount, 0.09),
            "cgst_amount": self.get_gst_amount(booking.total_amount, 0.09),
            "gst_amount": self.get_gst_amount(booking.total_amount, 0.09) * 2,
        }
        return render(request, "booking/booking_ticket.html", context=context)
