from django.utils import timezone
from weasyprint import HTML
import qrcode
import os
import io, base64

BASE_GENERATED_DIR = os.environ.get("GENERATED_DIR_CONTAINER_PATH")


def ensure_directory_exists(directory):
    """
    Ensure that the directory exists. If it doesn't, create it.

    Args:
    - directory: The path of the directory to check/create.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Directory '{directory}' created.")
    else:
        print(f"Directory '{directory}' already exists.")


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


def html_to_pdf(html_url: str, output_path) -> None:
    HTML(url=html_url).render().write_pdf(output_path)
