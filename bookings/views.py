import os
from typing import Any
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.views.generic import FormView, TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
import django_rq
import logging
import requests

from bookings.models import Booking, BookingCanteen, BookingCostume, BookingLocker, Payment
from custom_auth.models import User
from common_config.common import ADMIN_USER, BOUNCER_USER, COSTUME_MANAGER_USER, GATE_MANAGER_USER, CANTEEN_MANAGER_USER, LOCALHOST_URL, PAYMENT_MODES, LOCKER_MANAGER_USER
from management_core.models import TicketPrice
from .forms import BookingCostumeFormSet, BookingForm, BouncerCheckInForm, CanteenCardForm, LockerEditFormSet, LockerReturnFormSet, PaymentRecordForm, PaymentRecordEditForm, get_locker_add_formset
from .webhook_utils import handle_razorpay_webhook_booking_payment
from .ticket.utils import generate_booking_id_qrcode
from whatsapp.messages.message_handlers import send_booking_ticket, whatsapp_config
from .decorators import user_type_required

logging.getLogger(__name__)

default_queue = django_rq.get_queue("default")
low_queue = django_rq.get_queue("low")


@login_required
def admin_home_redirect(request: HttpRequest) -> HttpResponse:
    user : User = request.user
    if user.user_type == ADMIN_USER:
        return redirect("/admin_home")
    elif user.user_type == GATE_MANAGER_USER:
        return redirect("/bookings/")
    elif user.user_type == COSTUME_MANAGER_USER:
        return redirect("/bookings/costume")
    elif user.user_type == CANTEEN_MANAGER_USER:
        return redirect("/bookings/canteen/")
    return redirect("/frontend")


@login_required
def qr_code_homepage_redirect(request: HttpRequest, booking_id: str) -> HttpResponse:
    user: User = request.user
    if user.user_type in [ADMIN_USER, GATE_MANAGER_USER]:
        return redirect(f"/bookings/booking/{booking_id}/summary")
    if user.user_type == COSTUME_MANAGER_USER:
        return redirect(f"/bookings/booking/{booking_id}/costume/summary")
    if user.user_type == BOUNCER_USER:
        return redirect(f"/bookings/booking/{booking_id}/bouncer/summary")
    if user.user_type == CANTEEN_MANAGER_USER:
        return redirect(f"/bookings/booking/{booking_id}/canteen/card")
    if user.user_type == LOCKER_MANAGER_USER:
        return redirect(f"/bookings/booking/{booking_id}/locker/summary")
    return redirect("/bookings")


class RazorpayPaymentWebhookAPIView(APIView):
    # TODO remove this method after setting up the webhook
    # def get(self, request: Request) -> Response:
    #     try:
    #         data = request.GET
    #         handling_status = handle_razorpay_webhook_booking_payment(data)
    #         if not handling_status:
    #             return Response(status=status.HTTP_400_BAD_REQUEST)
    #         return Response(200)
    #     except Exception as e:
    #         logging.exception(e)
    #         return Response(status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request: Request) -> Response:
        try:
            data = request.data
            logging.info(f"Razorpay Webhook Data: {data}")
            handling_status = handle_razorpay_webhook_booking_payment(data)
            if not handling_status:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            return Response(200)
        except Exception as e:
            logging.exception(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        

class PrivacyPolicyTemplateView(TemplateView):
    template_name = "privacy_policy.html"


class AdminDataDashboard(APIView):
    def get(self, request: Request) -> Response:
        from_date = request.GET.get("from_date", timezone.localtime(timezone.now()).date().strftime("%d-%m-%Y"))
        to_date = request.GET.get("to_date", timezone.localtime(timezone.now()).date().strftime("%d-%m-%Y"))
        
        from_date = timezone.datetime.strptime(from_date, "%d-%m-%Y").date()
        to_date = timezone.datetime.strptime(to_date, "%d-%m-%Y").date()
        bookings = Booking.objects.filter(date__range=[from_date, to_date],
                                                              received_amount__gt=0).values_list("date", 
                                                                                                               "adult_male",
                                                                                                               "adult_female",
                                                                                                               "child",
                                                                                                               "booking_type",
                                                                                                               "total_amount",
                                                                                                               "received_amount",)
        # FIXME currently I am counting the advance payment in that date income instead of booking date income                          
        payments = Payment.objects.prefetch_related("booking").filter(
            booking__date__range=[from_date, to_date], 
            is_confirmed=True,
        ).values_list("booking__date", 
                      "amount", 
                      "payment_mode", 
                      "payment_for",
                      "is_returned_to_customer",)
        total_bookings = len(bookings)
        total_persons = 0
        person_type = {
            "adult_male": 0,
            "adult_female": 0,
            "child": 0,
        }
        date_wise_persons = {}
        for booking in bookings:
            date = booking[0].strftime("%d-%m-%Y")
            booking_total_person = booking[1] + booking[2] + booking[3]
            total_persons += booking_total_person
            person_type["adult_male"] += booking[1]
            person_type["adult_female"] += booking[2]
            person_type["child"] += booking[3]
            if date in date_wise_persons:
                date_wise_persons[date] += booking_total_person
            else:
                date_wise_persons[date] = booking_total_person
        date_wise_persons = [{"date": timezone.datetime.strptime(date, "%d-%m-%Y"),
                              "total_persons": total_persons}
                            for date, total_persons in date_wise_persons.items()]
        date_wise_persons.sort(key=lambda x: x["date"])
        total_persons_line_chart = [{"x": data["date"].strftime("%d-%m-%Y"), "y": data["total_persons"]} for data in date_wise_persons]
        person_type_pie_chart = [
            {
                "x": "Adult (Male)",
                "y": person_type["adult_male"]
            },
            {
                "x": "Adult (Female)",
                "y": person_type["adult_female"]
            },
            {
                "x": "Child",
                "y": person_type["child"]
            },
        ]
        
        total_income = 0
        total_gateway_income = 0
        total_gate_cash = 0
        total_gate_upi = 0
        payment_methods_income = {
            "gate_cash": 0,
            "gate_upi": 0,
            "payment_gateway": 0,
        }
        payment_methods_returned = {
            "gate_cash": 0,
            "gate_upi": 0,
            "payment_gateway": 0,
        }
        date_wise_income = {}
        payment_source_data = {
            "gate_income": 0,
            "costume_return": 0,
            "locker_deposit": 0,
            "locker_return": 0
        }
        for payment in payments:
            if payment[3] == "locker":
                if payment[4]:
                    payment_source_data["locker_return"] += payment[1]
                else:
                    payment_source_data["locker_deposit"] += payment[1]
            elif payment[3] == "costume_return":
                if payment[4]:
                    payment_source_data["costume_return"] += payment[1]
            elif payment[3] == "booking":
                if payment[4]:
                    pass
                else:
                    payment_source_data["gate_income"] += payment[1]
            date = payment[0].strftime("%d-%m-%Y")
            if payment[4]: # If it's returned to customer than it will be reduced from the total income
                total_income -= payment[1]
                payment_methods_returned[payment[2]] += payment[1]
            else:
                total_income += payment[1]
                payment_methods_income[payment[2]] += payment[1]
            if payment[4]: # Do not count the returned amount in the payment methods
                pass
            elif payment[2] == "gate_cash":
                total_gate_cash += payment[1]
            elif payment[2] == "gate_upi":
                total_gate_upi += payment[1]
            elif payment[2] == "payment_gateway":
                total_gateway_income += payment[1]
                
            if date in date_wise_income:
                date_wise_income[date] += (-payment[1]) if payment[4] else payment[1]
            else:
                date_wise_income[date] = (-payment[1]) if payment[4] else payment[1]
        date_wise_income = [{"date": timezone.datetime.strptime(date, "%d-%m-%Y"),
                            "total_income": total_income}
                            for date, total_income in date_wise_income.items()]
        date_wise_income.sort(key=lambda x: x["date"])
        
        total_income_line_chart = [{"x": data["date"].strftime("%d-%m-%Y"), "y": data["total_income"]} for data in date_wise_income]
        payment_method_income_pie_chart = [{"x": key, "y": value} for key, value in payment_methods_income.items()]
        payment_method_returned_pie_chart = [{"x": key, "y": value} for key, value in payment_methods_returned.items()]
        
        return Response({
            "total_bookings": total_bookings,
            "total_income": total_income,
            "total_persons": total_persons,
            "payment_method_income_pie_chart": payment_method_income_pie_chart,
            "payment_method_returned_pie_chart": payment_method_returned_pie_chart,
            "person_type_pie_chart": person_type_pie_chart,
            "total_persons_line_chart": total_persons_line_chart,
            "total_income_line_chart": total_income_line_chart,
            **payment_source_data
        }, status=status.HTTP_200_OK)
        

class AdminDashboardTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "admin_dashboard.html"
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        embed_url = os.environ.get("ADMIN_DASHBOARD_EMBED_URL")
        return {
            "dashboard_embed_url": embed_url
        }
    
    @user_type_required([ADMIN_USER])
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)

## GATE MANAGEMENT VIEWS

class BookingHomeTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "booking/booking_home.html"
    
    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)


class BookingHomeSummaryTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "booking/booking_home_summary.html"
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        bookings = Booking.objects.prefetch_related("booking_costume").filter(date=timezone.localtime(timezone.now()).date(), received_amount__gt=0)
        total_amount = 0
        total_costumes = 0
        costumes: list[BookingCostume] = []
        for booking in bookings:
            costumes.extend(booking.booking_costume.all())
        for costume in costumes:
            total_costumes += costume.quantity
            total_amount += costume.deposit_amount
        
        return {"costume_total_deposit": total_amount, "total_costumes": total_costumes, "date": timezone.localtime(timezone.now()).date(),}
    
    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)


class BookingFormView(LoginRequiredMixin, FormView):
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

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)
    
    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return super().post(request, *args, **kwargs)
    

class BookingEditFormView(LoginRequiredMixin, FormView):
    template_name = "booking/booking_edit.html"
    form_class = BookingForm

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
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
                booking.costume_received_amount if booking.is_discounted_booking else 0
            ),
            **{costume.costume.name: costume.quantity for costume in costumes},
        }

        form = BookingForm(initial=initial_data)
        return render(
            request,
            "booking/booking_edit.html",
            context={"form": form, "booking_id": booking_id},
        )
    
    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return super().post(request, *args, **kwargs)
    
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


class PaymentFormView(LoginRequiredMixin, FormView):
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

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
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

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        try:
            form.save()
            return super().form_valid(form)
        except Exception as e:
            return super().form_invalid(form)

    def get_success_url(self) -> str:
        return f"/bookings/booking/{self.kwargs.get('booking_id')}/summary"


class PaymentEditFormView(LoginRequiredMixin, FormView):
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

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
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

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: PaymentRecordEditForm):
        try:
            booking = form.save(payment_id=self.kwargs.get("payment_id"))
            self.booking_id = booking.id
            return super().form_valid(form)
        except Exception as e:
            return super().form_invalid(form)

    def get_success_url(self) -> str:
        return f"/bookings/booking/{self.booking_id}/payment-records"


class BookingSummaryCardTemplateView(LoginRequiredMixin, TemplateView):
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
            "costume_amount": booking.costume_received_amount,
            "total_amount": booking.total_amount,
            "received_amount": booking.received_amount,
            "amount_to_collect": booking.total_amount - booking.received_amount,
            "is_confirmed": booking.total_amount == booking.received_amount,
            "is_today_booking": booking.date == timezone.localtime(timezone.now()).date(),
        }
        return context

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
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


class BookingDeleteAPIView(APIView):
    def get(self, request, booking_id):
        secret = request.GET.get("secret")
        if secret != "terminate9045":
            return Response(status=400)
        try:
            Booking.objects.get(id=booking_id).delete()
            return Response(status=200)
        except Exception as e:
            return Response(status=500)


class BookingPaymentRecordsTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "booking/booking_payment_records.html"

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
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
            "phone_number": booking.wa_number,
            "date": booking.date,
            "booking_payments": booking.booking_payment.all(),
        }
        return render(request, self.template_name, context=context)


class BookingHistoryTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "booking/booking_history.html"
    PAGE_SIZE = 50

    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
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
        context = {
            "bookings": bookings,
        }
        return render(request, self.template_name, context=context)


class CronHandlerAPIView(APIView):
    def get(self, request: Request) -> Response:
        try:
            security_code = request.GET.get("security_code")
            if security_code != "9045":
                return Response(status=status.HTTP_400_BAD_REQUEST)
            current_time = timezone.localtime(timezone.now()).hour
            if cache.get("daily_cron_run_flag") or current_time < 19:
                return Response(status=500)
            today_date = timezone.localtime(timezone.now()).date()
            payments = Payment.objects.prefetch_related("booking").filter(is_confirmed=True, booking__date=today_date)
            bookings_record = {}
            for payment in payments:
                booking_id = str(payment.booking.id)
                if not bookings_record.get(booking_id, True):
                    continue                
                elif payment.payment_mode == "gate_cash":    
                    bookings_record[booking_id] = True
                else:
                    bookings_record[booking_id] = False
            
            bookings = []
            for booking_id, is_confirmed in bookings_record.items():
                if is_confirmed:
                    bookings.append(booking_id)
                                
            total_amount = 0
            for i in payments:
                if str(i.booking.id) in bookings:
                    total_amount += i.amount
            with transaction.atomic():
                today_date_str = today_date.strftime("%d-%m-%Y")
                res = requests.get(f"{LOCALHOST_URL}/bookings/api/dashboard?from_date={today_date_str}&to_date={today_date_str}")
                data = res.json()
                adjusted_amount = total_amount // 2
                today_bookings = Booking.objects.filter(date=today_date).order_by("total_amount")
                current_amount = 0
                for b in today_bookings:
                    if str(b.id) in bookings:
                        current_amount += b.received_amount - b.returned_amount
                        if current_amount >= adjusted_amount:
                            current_amount -= b.received_amount - b.returned_amount
                            break
                        b.update_booking()
                data["total_only_cash"] = total_amount
                data["adjusted_amount"] = current_amount
                person_type_str = ", ".join([f"{i['x']}: {i['y']}" for i in data["person_type_pie_chart"]])
                payment_type_income_str = ", ".join([f"{i['x']}: {i['y']}" for i in data["payment_method_income_pie_chart"]])
                payment_type_return_str = ", ".join([f"{i['x']}: {i['y']}" for i in data["payment_method_returned_pie_chart"]])
                message_str = f"Date: {today_date_str}\nTotal Bookings: {data["total_bookings"]}\nTotal Income: {data["total_income"]}\nTotal Persons: {data["total_persons"]}\nTotal Only Cash: {total_amount}\nAdjusted Amount: {current_amount}\nPayment Methods(Income): {payment_type_income_str}\nPayment Methods(Return): {payment_type_return_str}\nPerson Type: {person_type_str}"
                res = whatsapp_config.send_message(os.environ.get("ADMIN_WHATSAPP_NUMBER"), "text", {"body": message_str})
                cache.set("daily_cron_run_flag", True, timeout=18000)
                return Response(status=status.HTTP_200_OK)
        except Exception as e:
            logging.exception(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)

class SaveBookingTicketAPIView(APIView):
    @user_type_required([ADMIN_USER, GATE_MANAGER_USER])
    def get(self, request: Request, booking_id: str) -> Response:
        try:
            if not booking_id:
                return Response(
                    {"error": "Booking ID is required."}, status=status.HTTP_400_BAD_REQUEST
                )
            booking = Booking.objects.get(id=booking_id)
            send_booking_ticket(booking)            
            return Response(status=status.HTTP_200_OK)
        except Booking.DoesNotExist as e:
            return Response(
                {"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logging.exception(e)
            return Response(status=status.HTTP_200_OK)


## COSTUME MANAGEMENT VIEWS
class CostumeHomeTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "costume/costume_home.html"
    
    @user_type_required([ADMIN_USER, COSTUME_MANAGER_USER])
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)

class CostumeSummaryTemplateView(TemplateView):
    template_name = "costume/costume_summary.html"
    
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
        costume_data = booking.booking_costume.all()
        is_confirmed = True
        if booking.received_amount < booking.total_amount :
            is_confirmed = False
            
        is_today_booking = False
        if booking.date == timezone.localtime(timezone.now()).date():
            is_today_booking = True            
            
        is_costume_issue_remaining = False
        total_costume_returned_amount = 0
        for costume in costume_data:
            costume.remaining = costume.quantity - costume.issued_quantity
            total_costume_returned_amount += costume.returned_amount
            if costume.remaining > 0:
                is_costume_issue_remaining = True
            
        is_issuable = False
        if is_confirmed and is_today_booking and is_costume_issue_remaining:
            is_issuable = True
            
            
        context = {
            "booking_id": booking.id,
            "costume_amount": booking.costume_received_amount,
            "total_amount": booking.total_amount,
            "received_amount": booking.received_amount,
            "returned_amount": booking.returned_amount,
            "costume_returned_amount": total_costume_returned_amount,
            "wa_number": booking.wa_number,
            "date": booking.date,
            "adult_male": booking.adult_male,
            "adult_female": booking.adult_female,
            "child": booking.child,
            "is_confirmed": is_confirmed,
            "is_today_booking": is_today_booking,
            "is_issuable": is_issuable,
            "booking_costumes": costume_data,
        }        
        return render(request, "costume/costume_summary.html", context=context)


class IssueCostumesAPIView(APIView):
    def get(self, request, booking_id):
        if not request.user:
            return Response(
                {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            if not booking_id:
                return render(
                    request,
                    "common/error_page.html",
                    {"error_message": "Booking ID is required."},
                )
            booking = Booking.objects.filter(id=booking_id).exists()
            issue_number = int(request.GET.get("issue_number", 0))
            if not booking:
                return render(
                    request,
                    "common/error_page.html",
                    {"error_message": "Booking not found."},
                )
            booking = Booking.objects.prefetch_related(
                "booking_costume", "booking_costume__costume"
            ).get(id=booking_id)
            costume_data: list[BookingCostume] = booking.booking_costume.all()
            
            with transaction.atomic():
                current_number = 0
                
                for costume in costume_data:
                    if current_number >= issue_number:
                        break
                    remaining_costume = costume.quantity - costume.issued_quantity
                    if remaining_costume >= issue_number - current_number:
                        costume.issued_quantity += issue_number - current_number
                        current_number += issue_number - current_number
                        costume.save()
                    else:
                        costume.issued_quantity += remaining_costume
                        current_number += remaining_costume
                        costume.save()
                if current_number != issue_number:
                    raise Exception("Please enter correct issue number.")
            return Response(200)
        except Exception as e:
            logging.exception(e)
            return Response({
                "error": f"Error in issuing costumes. error: {e.args[0]}"
            }, status=status.HTTP_400_BAD_REQUEST)        


class BookingCostumeReturnFormView(FormView):
    template_name = "costume/costume_return.html"
    form_class = BookingCostumeFormSet
    
    def get_context_data(self, form=None, **kwargs: Any) -> dict[str, Any]:
        booking_id = self.kwargs.get("booking_id")
        booking = Booking.objects.prefetch_related(
            "booking_costume", "booking_costume__costume"
        ).get(id=booking_id)
        costume_data: list[BookingCostume] = booking.booking_costume.all()
        
        if not form:
            form = BookingCostumeFormSet(
                initial=[{"id": costume, 
                            "name": costume.costume.name, 
                            "quantity": costume.quantity, 
                            "issued_quantity": costume.issued_quantity, 
                            "returned_quantity": costume.returned_quantity, 
                            "returned_amount": costume.returned_amount
                        } for costume in costume_data])
        context = {
            "booking": booking,
            "formset": form,
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
        return render(request, "costume/costume_return.html", context=context)
    
    def form_valid(self, form):
        try:
            form.is_valid()
            with transaction.atomic():
                previous_total_returned_amount = 0
                total_returned_amount = 0
                booking = None
                for individual_form in form:
                    res = individual_form.save()                
                    booking_costume: BookingCostume = res[0]
                    previous_returned_amount = res[1]
                    
                    previous_total_returned_amount += previous_returned_amount
                    total_returned_amount += booking_costume.returned_amount
                    if not booking:
                        booking = booking_costume.booking
                payment = Payment.objects.prefetch_related("booking").filter(booking=booking, payment_for="costume_return", is_returned_to_customer=True, is_confirmed=True)
                if payment.exists():
                    payment = payment.first()
                else:
                    payment = Payment()
                payment.booking = booking
                payment.payment_mode = "gate_cash"
                payment.payment_for = "costume_return"
                payment.amount = total_returned_amount
                payment.is_confirmed = True
                payment.is_returned_to_customer = True
                payment.save()
                payment.booking.returned_amount -= previous_total_returned_amount
                payment.booking.returned_amount += total_returned_amount
                payment.booking.save()
            return super().form_valid(form)
        except Exception as e:
            return super().form_invalid(form)

    def get_success_url(self) -> str:
        return f"/bookings/booking/{self.kwargs.get('booking_id')}/costume/summary"
    

## BOUNCER MANAGEMENT VIEWS
class BouncerSummaryCardTemplateView(LoginRequiredMixin, FormView):
    template_name = "bouncer_summary.html"
    form_class = BouncerCheckInForm

    def get_context_data(self, form: BouncerCheckInForm|None=None, **kwargs: Any) -> dict[str, Any]:
        booking_id = self.kwargs.get("booking_id")
        booking = Booking.objects.get(id=booking_id)
        
        is_confirmed = True
        if booking.received_amount < booking.total_amount :
            is_confirmed = False
            
        is_today_booking = False
        if booking.date == timezone.localtime(timezone.now()).date():
            is_today_booking = True    
            
        if not form:
            form = BouncerCheckInForm(initial={
                "checked_in": booking.total_checked_in
            })            
            
        context = {
            "booking_id": booking.id,
            "total_amount": booking.total_amount,
            "received_amount": booking.received_amount,
            "wa_number": booking.wa_number,
            "date": booking.date,
            "adult_male": booking.adult_male,
            "adult_female": booking.adult_female,
            "child": booking.child,
            "is_confirmed": is_confirmed,
            "is_today_booking": is_today_booking,
            "total_person": booking.total_persons(),
            "total_checked_in": booking.total_checked_in,
            "form": form
        }      
        return context
    
    @user_type_required([ADMIN_USER, BOUNCER_USER])
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
        
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context=context)

    def form_valid(self, form: BouncerCheckInForm):
        try:
            booking_id = self.kwargs.get("booking_id")
            booking = Booking.objects.get(id=booking_id)
            form.save(booking)
            return super().form_valid(form)
        except Exception as e:
            logging.exception(e)
            return super().form_invalid(form)
    
    def get_success_url(self) -> str:
        return reverse("bouncer_ticket_summary", kwargs={"booking_id": self.kwargs.get("booking_id")})

## CANTEEN MANAGEMENT VIEWS
class CanteenCardFormView(FormView):
    template_name = "canteen/canteen_card.html"
    form_class = CanteenCardForm

    def get_context_data(self, form=None, **kwargs: Any) -> dict[str, Any]:
        booking_id = self.kwargs.get("booking_id")
        canteen_card = BookingCanteen.objects.prefetch_related("booking").get(booking_id=booking_id)
        booking = canteen_card.booking
        
        if not form:
            form = self.form_class()
        
        total_persons = booking.adult_male + booking.adult_female + booking.child
        context = {
            "form": form,
            "wa_number": booking.wa_number,
            "booking_id": booking.id,
            "date": booking.date,
            "total_persons": total_persons,
            "breakfast_quantity_used": canteen_card.breakfast_quantity_used,
            "available_breakfast": max(0, total_persons - canteen_card.breakfast_quantity_used),
            "lunch_quantity_used": canteen_card.lunch_quantity_used,
            "available_lunch": max(0, total_persons - canteen_card.lunch_quantity_used),
            "evening_snacks_quantity_used": canteen_card.evening_snacks_quantity_used,
            "available_evening_snacks": max(0, total_persons - canteen_card.evening_snacks_quantity_used),
        }
        
        return context    

    @user_type_required([ADMIN_USER, CANTEEN_MANAGER_USER])
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            booking_id = kwargs.get("booking_id")
            if not booking_id:
                return render(
                    request,
                    "common/error_page.html",
                    {"error_message": "Booking ID is required."},
                )
            canteen_card = BookingCanteen.objects.filter(booking_id=booking_id).exists()
            if not canteen_card:
                return render(
                    request,
                    "common/error_page.html",
                    {"error_message": "Canteen card not found for this booking."},
                )
            context = self.get_context_data(**kwargs)
            return render(request, self.template_name, context=context)
        except Exception as e:
            logging.exception(e)
            return render(
                request,
                "common/error_page.html",
                {"error_message": f"Error: {e.args[0]}"},
            )
    
    def form_valid(self, form: Any) -> HttpResponse:
        try:
            booking_id = self.kwargs.get("booking_id")
            canteen_card = BookingCanteen.objects.get(booking_id=booking_id)
            form.save(canteen_card)
            return render(self.request, "success_screen.html", {"message": "Canteen card updated successfully."})
        except Exception as e:
            logging.exception(e)
            return super().form_invalid(form)


## LOCKER MANAGEMENT VIEWS
class LockerSummaryTemplateView(TemplateView):
    template_name = "locker/locker_summary.html"
    
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
            "booking_locker", "booking_locker__locker"
        ).get(id=booking_id)
        locker_data: list[BookingLocker] = booking.booking_locker.all()
        is_confirmed = True
        if booking.received_amount < booking.total_amount :
            is_confirmed = False
            
        is_today_booking = False
        if booking.date == timezone.localtime(timezone.now()).date():
            is_today_booking = True            
            
        total_locker_returned_amount = 0
        total_deposit_amount = 0
        for locker in locker_data:
            total_deposit_amount += locker.deposit_amount
            total_locker_returned_amount += locker.returned_amount

        context = {
            "booking_id": booking.id,
            "locker_deposit_amount": total_deposit_amount,
            "total_amount": booking.total_amount,
            "received_amount": booking.received_amount,
            "returned_amount": booking.returned_amount,
            "locker_returned_amount": total_locker_returned_amount,
            "wa_number": booking.wa_number,
            "date": booking.date,
            "is_confirmed": is_confirmed,
            "is_today_booking": is_today_booking,
            "booking_locker": locker_data,
        }
        return render(request, self.template_name, context=context)


def send_locker_update_whatsapp_message(receiver:str, date: str, locker_numbers: list[int|str]) -> None:
    """Send the locker update message to the receiver.

    :param receiver: The receiver's phone number.
    :param locker_numbers: The locker numbers to be sent in the message.  
    """
    message = f"Your Issued lockers for booking on {date} are:\n {', '.join(locker_numbers)}"
    whatsapp_config.send_message(receiver, "text", {
        "body": message
    })

class LockerAddFormView(FormView):
    template_name = "locker/locker_add.html"
    form_class = get_locker_add_formset(1)
    
    def get_context_data(self, form=None, **kwargs: Any) -> dict[str, Any]:
        booking_id = self.kwargs.get("booking_id")
        booking = Booking.objects.prefetch_related().get(id=booking_id)
        total_locker: str = self.request.GET.get("total_locker", "0")
        payment_mode = self.request.GET.get("payment_mode")
        if not form:
            if total_locker and total_locker.isnumeric() and payment_mode:
                total_locker = int(total_locker)
                formset = get_locker_add_formset(total_locker)
            else:
                formset = get_locker_add_formset(1)()
        else:
            formset = form
        context = {
            "booking_id": booking_id,
            "wa_number": booking.wa_number,
            "date": booking.date,
            "formset": formset,
            "payment_mode": payment_mode
        }
        
        return context
    
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        booking_id = kwargs.get("booking_id")
        total_locker = request.GET.get("total_locker")
        payment_mode = request.GET.get("payment_mode")
        
        if not booking_id:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking ID is required."},
            )
        # This is to redirect the user to the ask page to ask total forms to generate for add locker.
        if not total_locker or not payment_mode:
            return render(request, "locker/locker_add_ask.html", context={"booking_id": booking_id, "payment_modes": PAYMENT_MODES})
        
        booking = Booking.objects.filter(id=booking_id).exists()
        if not booking:
            return render(
                request,
                "common/error_page.html",
                {"error_message": "Booking not found."},
            )
        
        context = self.get_context_data()
        
        return render(request, "locker/locker_add.html", context=context)

    def form_valid(self, form: Any) -> HttpResponse:
        try:
            form.is_valid()
            with transaction.atomic():
                booking = Booking.objects.get(id=self.kwargs.get("booking_id"))
                booking_forms = []
                total_deposit_amount = 0
                locker_numbers = []
                for single_form in form:
                    res: BookingLocker = single_form.save(booking)
                    locker_numbers.append(str(res.locker.locker_number))
                    booking_forms.append(res)
                    total_deposit_amount += res.deposit_amount
                
                locker_payment = Payment.objects.filter(booking=booking, payment_for="locker", is_confirmed=True, is_returned_to_customer=False)
                if locker_payment.exists():
                    locker_payment = locker_payment.first()
                else:
                    locker_payment = Payment(booking=booking, payment_for="locker", is_confirmed=True, is_returned_to_customer=False)                    
                locker_payment.payment_mode = self.request.GET.get("payment_mode")
                # Adding the deposit amount here because only new entries will be added to the locker_payment via this view
                locker_payment.amount += total_deposit_amount
                booking.received_amount += total_deposit_amount
                booking.total_amount += total_deposit_amount
                booking.locker_received_amount += total_deposit_amount
                booking.save()
                locker_payment.save()
                messages.success(self.request, "Locker added successfully.")
                # TODO enable this after implementing numbering on the key and lock of lockers.
                # default_queue.enqueue(
                #     send_locker_update_whatsapp_message,
                #     booking.wa_number,
                #     booking.date.strftime("%d-%m-%Y"),
                #     locker_numbers
                # )
                return redirect(reverse("locker_summary", kwargs={"booking_id": self.kwargs.get("booking_id")}))
        except Exception as e:
            logging.exception(e)
            return super().form_invalid(form)


class LockerEditFormView(FormView):
    template_name = "locker/locker_edit.html"
    form_class = LockerEditFormSet
    
    def get_context_data(self, form=None, **kwargs: Any) -> dict[str, Any]:
        booking_id = self.kwargs.get("booking_id")
        booking = Booking.objects.prefetch_related("booking_locker", "booking_locker__locker").get(id=booking_id)
        booking_lockers = booking.booking_locker.all()
        if not form:
            formset = LockerEditFormSet(queryset=booking_lockers)
        else:
            formset = form
        context = {
            "booking_id": booking_id,
            "wa_number": booking.wa_number,
            "date": booking.date,
            "formset": formset,
        }
        
        return context
    
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        try:
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
            
            context = self.get_context_data()
            
            return render(request, self.template_name, context=context)
        except Exception as e:
            logging.exception(e)
            return render(
                request,
                "common/error_page.html",
                {"error_message": f"Error: {e}"},
            )

    def form_valid(self, form: Any) -> HttpResponse:
        try:
            form.is_valid()
            with transaction.atomic():
                total_deposit_amount = 0
                updated_lockers = []
                for single_form in form:
                    res: BookingLocker = single_form.save()
                    total_deposit_amount += res.deposit_amount
                    updated_lockers.append(str(res.locker.locker_number))
                booking = Booking.objects.get(id=self.kwargs.get("booking_id"))
                booking_payment = Payment.objects.filter(booking=booking, payment_for="locker", is_confirmed=True, is_returned_to_customer=False)
                if booking_payment.exists():
                    booking_payment = booking_payment.first()
                    booking.locker_received_amount -= booking_payment.amount
                    booking.total_amount -= booking_payment.amount
                    booking.received_amount -= booking_payment.amount
                else:
                    booking_payment = Payment(booking=booking, payment_for="locker", is_confirmed=True, is_returned_to_customer=False)
                booking_payment.payment_mode = "gate_cash"
                booking_payment.amount = total_deposit_amount
                booking.total_amount += total_deposit_amount
                booking.received_amount += total_deposit_amount
                booking.locker_received_amount += total_deposit_amount
                booking.save()
                booking_payment.save()
                messages.success(self.request, "Lockers edited successfully.")
                # TODO enable this after implementing numbering on the key and lock of lockers.
                # default_queue.enqueue(
                #     send_locker_update_whatsapp_message,
                #     booking.wa_number,
                #     booking.date.strftime("%d-%m-%Y"),
                #     updated_lockers
                # )
                return redirect(reverse("locker_summary", kwargs={"booking_id": self.kwargs.get("booking_id")}))
        except Exception as e:
            logging.exception(e)
            return super().form_invalid(form)


class LockerReturnFormView(FormView):
    template_name = "locker/locker_return.html"
    form_class = LockerReturnFormSet
    
    def get_context_data(self, form=None, **kwargs: Any) -> dict[str, Any]:
        booking_id = self.kwargs.get("booking_id")
        booking = Booking.objects.prefetch_related("booking_locker", "booking_locker__locker").get(id=booking_id)
        booking_lockers = booking.booking_locker.all()
        if not form:
            formset = LockerReturnFormSet(queryset=booking_lockers)
        else:
            formset = form
        context = {
            "booking_id": booking_id,
            "wa_number": booking.wa_number,
            "date": booking.date,
            "formset": formset,
        }
        
        return context
    
    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        try:
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
            
            context = self.get_context_data()
            
            return render(request, self.template_name, context=context)
        except Exception as e:
            logging.exception(e)
            return render(
                request,
                "common/error_page.html",
                {"error_message": f"Error: {e}"},
            )

    def form_valid(self, form: Any) -> HttpResponse:
        try:
            form.is_valid()
            with transaction.atomic():
                total_return_amount = 0
                for single_form in form:
                    res: BookingLocker = single_form.save()
                    total_return_amount += res.returned_amount
                booking = Booking.objects.get(id=self.kwargs.get("booking_id"))
                booking_payment = Payment.objects.filter(booking=booking, payment_for="locker", is_confirmed=True, is_returned_to_customer=True)
                if booking_payment.exists():
                    booking_payment = booking_payment.first()
                    booking.returned_amount -= booking_payment.amount
                    booking.locker_returned_amount -= booking_payment.amount
                else:
                    booking_payment = Payment(booking=booking, payment_for="locker", is_confirmed=True, is_returned_to_customer=True)
                booking_payment.payment_mode = "gate_cash"
                booking_payment.amount = total_return_amount
                booking.returned_amount += total_return_amount
                booking.locker_returned_amount += total_return_amount
                booking.save()
                booking_payment.save()
                messages.success(self.request, "Lockers edited successfully.")
                return redirect(reverse("locker_summary", kwargs={"booking_id": self.kwargs.get("booking_id")}))
        except Exception as e:
            logging.exception(e)
            return super().form_invalid(form)


class SendLockerUpdateMessageAPIView(APIView):
    def get(self, request: Request, booking_id: str) -> Response:
        try:
            lockers = BookingLocker.objects.prefetch_related("booking").filter(booking_id=booking_id)
            locker_numbers = []
            booking_number = None
            booking_date = None
            for locker in lockers:
                if not booking_number:
                    booking_number = locker.booking.wa_number
                    booking_date = locker.booking.date
                locker_numbers.append(str(locker.locker.locker_number))
            
            if locker_numbers:
                default_queue.enqueue(
                    send_locker_update_whatsapp_message,
                    booking_number,
                    booking_date.strftime("%d-%m-%Y"),
                    locker_numbers
                )
            else:
                default_queue.enqueue(
                    whatsapp_config.send_message,
                    booking_number,
                    "text",
                    {"body": f"No locker issued for this booking for date: {booking_date.strftime("%d-%m-%Y")}"}
                )
            return Response(200)
        except Exception as e:
            logging.exception(e)
            return Response(500)
        
