import os
from typing import Any
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.views.generic import FormView, TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
import logging

from bookings.models import Booking, Payment
from common_config.common import LOCALHOST_URL, TEMPORARY_FILE_LOCATION
from management_core.models import TicketPrice
from .forms import BookingForm, PaymentRecordForm, PaymentRecordEditForm
from .utils import create_razorpay_order
from .ticket.utils import generate_booking_id_qrcode, html_to_pdf


logging.getLogger(__name__)


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
        return render(
            request,
            "booking/booking_edit.html",
            context={"form": form, "booking_id": booking_id},
        )
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs) 
        context["booking_id"] = self.kwargs.get("booking_id")
        return context
    
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
        return f"/bookings/booking/{self.kwargs.get("booking_id")}/payment"


class PaymentFormView(FormView):
    template_name = "booking/payment.html"
    form_class = PaymentRecordForm

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        booking_id = self.kwargs.get("booking_id")
        booking = Booking.objects.prefetch_related(
            "booking_costume", "booking_costume__costume"
        ).get(id=booking_id)
        costumes = booking.booking_costume.all
        if self.get_form().errors:
            form = self.get_form()
        else:
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

        return context

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
        context = self.get_context_data(**kwargs)
        return render(request, "booking/payment.html", context=context)

    def form_valid(self, form):
        try:
            form.save()
            return super().form_valid(form)
        except Exception as e:
            return super().form_invalid(form)

    def get_success_url(self) -> str:
        return f"/bookings/booking/{self.kwargs.get('booking_id')}/summary"


class PaymentEditFormView(FormView):
    template_name = "booking/booking_payment.html"
    form_class = PaymentRecordEditForm

    def get_context_data(self, form=None, **kwargs: Any) -> dict[str, Any]:
        payment_id = self.kwargs.get("payment_id")
        payment = Payment.objects.prefetch_related("booking").get(id=payment_id)
        if not form:
            form = PaymentRecordEditForm(
                initial={
                    "booking": payment.booking,
                    "payment_amount": payment.amount,
                    "payment_mode": payment.payment_mode,
                    "payment_for": payment.payment_for,
                    "is_confirmed": payment.is_confirmed,
                    "is_returned_to_customer": payment.is_returned_to_customer,
                }
            )
        
        self.booking_id = payment.booking.id
        context = {"form": form, "payment": payment, "booking_id": self.booking_id}
        return context

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        payment_id = kwargs.get("payment_id")
        if not payment_id:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Payment ID is required."},
            )
        payment = Payment.objects.filter(id=payment_id).exists()
        if not payment:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Payment not found."},
            )
        context = self.get_context_data(**kwargs)
        return render(request, "booking/booking_payment.html", context=context)

    def form_valid(self, form: PaymentRecordEditForm):
        try:
            booking = form.save(payment_id=self.kwargs.get("payment_id"))
            self.booking_id = booking.id
            return super().form_valid(form)
        except Exception as e:
            return super().form_invalid(form)

    def get_success_url(self) -> str:
        return f"/bookings/booking/{self.booking_id}/payment-records"


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
            "infant": booking.infant,
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


class BookingPaymentRecordsTemplateView(TemplateView):
    template_name = "booking/booking_payment_records.html"

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
        booking = Booking.objects.prefetch_related("booking_payment").get(id=booking_id)
        context = {
            "booking_id": booking.id,
            "booking_payments": booking.booking_payment.all(),
        }
        return render(request, self.template_name, context=context)


class BookingHistoryTemplateView(TemplateView):
    template_name = "booking/booking_history.html"
    PAGE_SIZE = 50

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        wa_number = request.GET.get("wa_number")
        page = request.GET.get("page", 1)
        bookings = Booking.objects.all().order_by("-date")
        if wa_number:
            bookings = bookings.filter(wa_number__contains=wa_number)

        try:
            paginator = Paginator(bookings, self.PAGE_SIZE)
            bookings = paginator.page(page)
        except PageNotAnInteger:
            bookings = paginator.page(1)
        except EmptyPage:
            bookings = paginator.page(paginator.num_pages)
        logging.info(f"Bookings: {bookings}")
        context = {
            "bookings": bookings,
        }
        return render(request, self.template_name, context=context)


class SaveBookingTicketAPIView(APIView):
    def get(self, request: Request, booking_id: str) -> Response:
        if not booking_id:
            return Response(
                {"error": "Booking ID is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        path = f"{TEMPORARY_FILE_LOCATION}/booking_tickets"
        os.makedirs(path, exist_ok=True)
        path = f"{path}/booking_{booking_id}.pdf"
        pdf = html_to_pdf(f"{LOCALHOST_URL}/bookings/booking/{booking_id}/ticket", path)
        return Response({"pdf": pdf}, status=status.HTTP_200_OK)
