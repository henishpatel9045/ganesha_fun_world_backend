from django.contrib import admin
from django.urls import path
from django.utils import timezone
from django.shortcuts import render
from import_export.admin import ImportExportModelAdmin
import logging

from bookings.models import BookingLocker
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
        "in_use_by",
        "is_available",
    )
    list_filter = ("is_available",)
    search_fields = ("locker_number",)
    list_editable = ("is_available",)
    list_per_page = 25

    def in_use_by(self, obj):
        if not obj.is_available:    
            locker = self.lockers_info.get(str(obj.locker_number))
            if locker:
                return f"{locker.booking.wa_number} - {locker.booking.date}"
        return ""

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

    def changelist_view(self, *args, **kwargs):
        self.booking_lockers = BookingLocker.objects.prefetch_related("booking", "locker").filter(
            is_returned=False
        )
        lockers_info = {}
        for locker in self.booking_lockers:
            lockers_info[str(locker.locker.locker_number)] = locker
        self.lockers_info = lockers_info
        return super().changelist_view(*args, **kwargs)


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
        "name",
        "type",
        "sent_order",
    )
    list_editable = ("sent_order",)


@admin.register(ExtraWhatsAppNumbers)
class ExtraWhatsAppNumbersAdmin(ImportExportModelAdmin):
    list_display = ("number",)
    search_fields = ("number",)
    resource_class = ExtraWANumbersResource
