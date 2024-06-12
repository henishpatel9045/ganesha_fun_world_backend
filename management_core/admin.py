from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from import_export.admin import ImportExportModelAdmin
import logging

from .models import (
    TicketPrice,
    Costume,
    Locker,
    WhatsAppInquiryMessage,
    ExtraWhatsAppNumbers,
)
from .forms import TicketListPriceForm, LockerBulkAddForm
from .resources import ExtraWANumbersResource


logging.getLogger(__name__)


@admin.register(TicketPrice)
class TicketPriceAdmin(admin.ModelAdmin):
    change_list_template = "management/admin_ticket_price_changelist.html"

    list_display = (
        "date",
        "adult",
        "child",
        "day",
    )
    list_filter = ("date",)
    search_fields = ("date",)
    date_hierarchy = "date"

    def day(self, obj):
        return obj.date.strftime("%A")

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("create-multi/", self.open_multi_slot_form),
        ]
        return my_urls + urls

    def open_multi_slot_form(self, request):
        return render(
            request,
            "management/bulk_ticket_price_list.html",
            context={"form": TicketListPriceForm()},
        )


@admin.register(Locker)
class LockerAdmin(admin.ModelAdmin):
    change_list_template = "management/locker_admin_changelist.html"

    list_display = (
        "locker_number",
        "is_available",
    )
    search_fields = ("locker_number",)
    list_editable = ("is_available",)
    list_per_page = 25

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("create-multi/", self.open_multi_slot_form),
        ]
        return my_urls + urls

    def open_multi_slot_form(self, request):
        return render(
            request,
            "management/bulk_locker_add_list.html",
            context={"form": LockerBulkAddForm()},
        )


@admin.register(Costume)
class CostumeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "is_available",
    )


@admin.register(WhatsAppInquiryMessage)
class WhatsAppInquiryMessageAdmin(admin.ModelAdmin):
    list_display = (
        "type",
        "sent_order",
    )
    list_editable = ("sent_order",)


@admin.register(ExtraWhatsAppNumbers)
class ExtraWhatsAppNumbersAdmin(ImportExportModelAdmin):
    list_display = ("number",)
    search_fields = ("number",)
    resource_class = ExtraWANumbersResource
    