from django.conf import settings
import os


HOST_URL = "https://leading-blindly-seahorse.ngrok-free.app"

BOOKING_TYPES = [
    ("gate_booking", "gate_booking"),
    ("whatsapp_booking", "whatsapp_booking"),
]

PAYMENT_MODES = [
    ("gate_upi", "gate_upi"),
    ("gate_cash", "gate_cash"),
    ("payment_gateway", "payment_gateway"),
]

PAYMENT_MODES_FORM = [("gate_cash", "Cash"), ("gate_upi", "UPI")]

PAYMENT_FOR = [
    ("booking", "booking"),
    ("locker", "locker"),
]


# CACHE_KEYS
COSTUME_CACHE_KEY = "costume_table_data"

LOCALHOST_URL = "http://localhost:8000"

GENERATED_MEDIA_BASE_URL = "/generated_media"

if os.environ.get("ENVIRONMENT") == "prod":
    TEMPORARY_FILE_LOCATION = "/home/ganesha/generated_media"
else:
    TEMPORARY_FILE_LOCATION = "/home/generated_media"
