# Generated by Django 5.0.4 on 2024-05-27 05:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0007_booking_locker_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookinglocker',
            name='is_returned',
            field=models.BooleanField(default=False),
        ),
    ]
