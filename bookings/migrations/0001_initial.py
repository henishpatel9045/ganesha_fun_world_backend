# Generated by Django 5.0.4 on 2024-05-01 03:41

import django.core.validators
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('management_core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('wa_number', models.CharField(db_index=True, max_length=15)),
                ('adult', models.PositiveIntegerField(default=0)),
                ('child', models.PositiveIntegerField(default=0)),
                ('booking_type', models.CharField(choices=[('gate_booking', 'gate_booking'), ('whatsapp_booking', 'whatsapp_booking')], default='gate_booking', max_length=50)),
                ('date', models.DateField(blank=True, null=True)),
                ('ticket_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('costume_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('received_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_discounted_booking', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BookingCanteen',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('breakfast_quantity_used', models.PositiveIntegerField(default=0)),
                ('lunch_quantity_used', models.PositiveIntegerField(default=0)),
                ('evening_snacks_quantity_used', models.PositiveIntegerField(default=0)),
                ('dinner_quantity_used', models.PositiveIntegerField(default=0)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_canteen', to='bookings.booking')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BookingCostume',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity', models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(1)])),
                ('deposit_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('returned_at', models.DateTimeField(blank=True, null=True)),
                ('returned_quantity', models.PositiveIntegerField(default=0)),
                ('returned_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_costume', to='bookings.booking')),
                ('costume', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='management_core.costume')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='BookingLocker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deposit_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('returned_at', models.DateTimeField(blank=True, null=True)),
                ('returned_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_locker', to='bookings.booking')),
                ('locker', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='management_core.locker')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('payment_mode', models.CharField(choices=[('gate_upi', 'gate_upi'), ('gate_cash', 'gate_cash'), ('payment_gateway', 'payment_gateway')], default='gate_upi', max_length=50)),
                ('payment_for', models.CharField(choices=[('booking', 'booking'), ('locker', 'locker')], default='booking', max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('payment_data', models.JSONField(blank=True, null=True)),
                ('is_confirmed', models.BooleanField(default=False)),
                ('is_returned_to_customer', models.BooleanField(default=False)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='booking_payment', to='bookings.booking')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
