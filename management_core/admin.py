from django.contrib import admin
from django.urls import path
from django.shortcuts import render
import logging

from .models import TicketPrice, Costume, Locker
from .forms import TicketListPriceForm


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


admin.site.register([Costume, Locker])
