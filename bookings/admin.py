from django.contrib import admin

from .models import Booking, Payment, BookingCostume, BookingCanteen, BookingLocker

# Register your models here.

admin.site.register([Booking, Payment, BookingCostume, BookingCanteen, BookingLocker])
