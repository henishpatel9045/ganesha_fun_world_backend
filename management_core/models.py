from django.db import models


class DateTimeBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Costume(DateTimeBaseModel):
    name = models.CharField(max_length=100, db_index=True, null=False)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    is_available = models.BooleanField(default=True)


class Locker(DateTimeBaseModel):
    locker_number = models.CharField(max_length=100, db_index=True, null=False)
    is_available = models.BooleanField(default=True)
