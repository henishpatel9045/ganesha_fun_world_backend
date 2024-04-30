from django.db import models
from django.core.cache import cache

from common_config.common import COSTUME_CACHE_KEY


class DateTimeBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TicketPrice(DateTimeBaseModel):
    date = models.DateField(db_index=True, null=False, unique=True)
    adult = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    child = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    breakfast_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    lunch_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    dinner_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    other_price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    other_price_description = models.TextField(null=True, blank=True)

    def __str__(self) -> COSTUME_CACHE_KEY:
        return f"{self.date}"


class Costume(DateTimeBaseModel):
    name = models.CharField(max_length=100, db_index=True, null=False)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    is_available = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        items = cache.get(COSTUME_CACHE_KEY)
        if items:
            items[str(self.id)] = {
                "name": self.name,
                "description": self.description,
                "price": self.price,
                "is_available": self.is_available,
            }
            cache.set(COSTUME_CACHE_KEY, items)
        else:
            items = {
                str(item.id): {
                    "name": item.name,
                    "description": item.description,
                    "price": item.price,
                    "is_available": item.is_available,
                }
                for item in Costume.objects.all()
            }
            cache.set(COSTUME_CACHE_KEY, items)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        items = cache.get(COSTUME_CACHE_KEY)
        if items:
            items.pop(str(self.id))
            cache.set(COSTUME_CACHE_KEY, items)
        super().delete(*args, **kwargs)


class Locker(DateTimeBaseModel):
    locker_number = models.CharField(max_length=100, db_index=True, null=False)
    is_available = models.BooleanField(default=True)
