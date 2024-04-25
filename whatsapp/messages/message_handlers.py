import requests
import os
from whatsapp.utils import WhatsAppClient

LOGO_URL = os.environ.get(
    "LOGO_URL", "https://www.shreeganeshafunworld.com/images/logo.png"
)


whatsapp_config = WhatsAppClient(api_key="YOUR", wa_id="YOUR")
client = whatsapp_config.get_client()


def send_welcome_message(recipient_number: str) -> requests.Response:
    """
    Function to send welcome message to the user.

    :param `recipient_number`: The number to which message is to be sent

    template_name used is `welcome_message`
    """
    message_type = "template"
    template_name = "welcome_message"
    type_data = {
        "name": template_name,
        "language": {"code": "en"},
        "components": [
            {
                "type": "header",
                "parameters": [{"type": "image", "image": {"link": LOGO_URL}}],
            },
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": "0",
                "parameters": [{"type": "payload", "payload": "welcome__inquiry"}],
            },
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": "1",
                "parameters": [{"type": "payload", "payload": "welcome__mybookings"}],
            },
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": "2",
                "parameters": [{"type": "payload", "payload": "welcome__booknow"}],
            },
        ],
    }

    response = whatsapp_config.send_message(recipient_number, message_type, type_data)
    return response

