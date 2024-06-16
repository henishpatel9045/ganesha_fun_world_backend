from typing import Any
from django.contrib import admin
from django.db.models.fields.related import RelatedField
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.utils import timezone

from .models import Booking, Payment, BookingCostume, BookingCanteen, BookingLocker

# Register your models here.
admin.site.site_title = "Shree Ganesha Fun World Management System"
admin.site.site_header = "Shree Ganesha Fun World Management System"
admin.site.site_url = "/home"


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = [
        "payment_mode",
        "payment_for",
        "amount",
        "is_confirmed",
        "is_returned_to_customer",
    ]
    show_change_link = True


class CostumeInline(admin.TabularInline):
    model = BookingCostume
    extra = 0
    show_change_link = True


class CanteenInline(admin.TabularInline):
    model = BookingCanteen
    extra = 0
    show_change_link = True


class LockerInline(admin.TabularInline):
    model = BookingLocker
    extra = 0
    show_change_link = True


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    inlines = [PaymentInline, CostumeInline, CanteenInline, LockerInline]
    list_display = [
        "wa_number",
        "date",
        "adult_male",
        "adult_female",
        "child",
        "booking_type",
        "total_amount",
        "received_amount",
        "is_today_booking",
    ]
    list_filter = [
        "date",
        "booking_type",
        "is_discounted_booking",
    ]
    search_fields = [
        "wa_number",
    ]
    date_hierarchy = "date"

    def is_today_booking(self, obj) -> bool:
        return "Yes" if obj.date == timezone.datetime.today().date() else "No"

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return (
            super()
            .get_queryset(request)
        )


@admin.register(Payment)
class PaymentModelAdmin(admin.ModelAdmin):
    list_display = [
        "booking",
        "payment_for",
        "payment_mode",
        "amount",
    ]
    search_fields = ["booking",]
    list_filter = ["payment_mode", "payment_for",]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).prefetch_related("booking")


@admin.register(BookingLocker)
class BookingLockerModelAdmin(admin.ModelAdmin):
    list_display = [
        "booking",
        # "locker__number",
    ]
    search_fields = ["booking"]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).prefetch_related("booking", "locker")


@admin.register(BookingCostume)
class BookingCostumeModelAdmin(admin.ModelAdmin):
    list_display = [
        "booking",
        # "costume__name",
    ]
    search_fields = ["booking",]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).prefetch_related("booking", "costume")


@admin.register(BookingCanteen)
class BookingCanteenModelAdmin(admin.ModelAdmin):
    list_display = [
        "booking",
    ]
    search_fields = ["booking",]
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).prefetch_related("booking")
