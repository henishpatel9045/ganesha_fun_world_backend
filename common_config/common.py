from django.conf import settings
import os


HOST_URL = "https://leading-blindly-seahorse.ngrok-free.app"

# USER RELATED CONSTANTS
ADMIN_USER = "admin"
GATE_MANAGER_USER = "gate_manager"
COSTUME_MANAGER_USER = "costume_manager"
LOCKER_MANAGER_USER = "locker_manager"
CANTEEN_MANAGER_USER = "canteen_manager"
BOUNCER_USER = "bouncer"

USER_TYPES = [
    (ADMIN_USER, ADMIN_USER),
    (GATE_MANAGER_USER, GATE_MANAGER_USER),
    (COSTUME_MANAGER_USER, COSTUME_MANAGER_USER),
    (LOCKER_MANAGER_USER, LOCKER_MANAGER_USER),
    (CANTEEN_MANAGER_USER, CANTEEN_MANAGER_USER),
    (BOUNCER_USER, BOUNCER_USER),
]

# BOOKING RELATED CONSTANTS
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
    ("costume_return", "costume_return"),
]


# CACHE_KEYS
LOCALHOST_URL = "http://localhost:8000"

GENERATED_MEDIA_BASE_URL = "/generated_media"

if os.environ.get("ENVIRONMENT") == "prod":
    TEMPORARY_FILE_LOCATION = "/home/ganesha/generated_media"
else:
    TEMPORARY_FILE_LOCATION = "/home/generated_media"
