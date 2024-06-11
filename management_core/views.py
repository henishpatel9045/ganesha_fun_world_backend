from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, TemplateView
from rest_framework.views import APIView
import logging

from .forms import (
    TicketListPriceForm,
    LockerBulkAddForm,
    TextOnlyPromotionalMessageForm,
)
from bookings.decorators import user_type_required
from common_config.common import ADMIN_USER

logging.getLogger(__name__)


class TicketListPriceFormView(LoginRequiredMixin, APIView):
    @user_type_required([ADMIN_USER])
    def post(self, request):
        form = TicketListPriceForm(request.POST)
        logging.info("Creating ticket price list: ", request.POST)
        # try:
        if form.is_valid():
            logging.info(f"Form is valid: {form.cleaned_data}")
            form.save()
        if form.errors:
            logging.warning(f"Form has errors: {form.errors}")
            return render(
                request, "management/bulk_ticket_price_list.html", {"form": form}
            )
        else:
            return HttpResponseRedirect("/admin/management_core/ticketprice/")


class LockerBulkAddFormView(LoginRequiredMixin, APIView):
    @user_type_required([ADMIN_USER])
    def post(self, request):
        form = LockerBulkAddForm(request.POST)
        logging.info("Creating locker list: ", request.POST)
        # try:
        if form.is_valid():
            logging.info(f"Form is valid: {form.cleaned_data}")
            form.save()
        if form.errors:
            logging.warning(f"Form has errors: {form.errors}")
            return render(
                request, "management/bulk_locker_add_list.html", {"form": form}
            )
        else:
            return HttpResponseRedirect("/admin/management_core/locker/")


class TextOnlyPromotionalMessageFormView(FormView):
    form_class = TextOnlyPromotionalMessageForm
    template_name = "promotional/only_text.html"
    success_url = "/bookings/"

    def form_valid(self, form: TextOnlyPromotionalMessageForm):
        try:
            form.send_messages()
            return super().form_valid(form)
        except Exception as e:
            return self.form_invalid(form)


class AdminHomeTemplateView(TemplateView):
    template_name = "admin_home.html"


class PromotionalHomeTemplateView(TemplateView):
    template_name = "promotional/home.html"
