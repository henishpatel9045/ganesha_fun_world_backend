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
