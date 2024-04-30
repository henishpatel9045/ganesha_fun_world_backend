from django.contrib import admin

from .models import TicketPrice, Costume, Locker

# Register your models here.

admin.site.register([TicketPrice, Costume, Locker])
