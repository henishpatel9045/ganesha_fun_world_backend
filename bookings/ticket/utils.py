from django.utils import timezone
from weasyprint import HTML
import qrcode
import os
import io, base64

from common_config.common import (
    GENERATED_MEDIA_BASE_URL,
    HOST_URL,
    LOCALHOST_URL,
    TEMPORARY_FILE_LOCATION,
)


def ensure_directory_exists(directory):
    """
    Ensure that the directory exists. If it doesn't, create it.

    Args:
    - directory: The path of the directory to check/create.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def generate_qr_code(data: str) -> None:
    """Generate QR code from data and save it to io object in memory and return the base64 encoded image

    :param data: data to be encoded in QR code

    :return: base64 encoded image of the generated QR code
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io)
    img_base64 = base64.b64encode(img_io.getvalue()).decode()
    return img_base64


def generate_booking_id_qrcode(booking_id: str) -> str:
    """Generate QR code for booking id

    :param booking_id: booking id to be encoded in QR code

    :return: base64 encoded image of the generated QR code
    """
    return generate_qr_code(booking_id)


def html_to_pdf(url: str, output_path: str) -> None:
    HTML(url=url).render().write_pdf(output_path)


def generate_ticket_pdf(booking_id: str) -> str:
    """Generate ticket pdf for the booking

    :param booking_id: booking id for which ticket is to be generated

    :return: path of the generated pdf
    """
    path = f"{TEMPORARY_FILE_LOCATION}/booking_tickets"
    os.makedirs(path, exist_ok=True)
    path = f"{path}/booking_{booking_id}.pdf"
    html_url = f"{HOST_URL}/bookings/booking/{booking_id}/ticket"
    html_to_pdf(html_url, path)
    return f"{HOST_URL}/{GENERATED_MEDIA_BASE_URL}/booking_tickets/booking_{booking_id}.pdf"
