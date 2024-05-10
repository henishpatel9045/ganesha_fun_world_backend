import requests


class WhatsAppClient:
    def __init__(self, api_key: str, wa_id: str) -> requests.Session:
        self.api_key = api_key
        self.wa_id = wa_id
        self.base_url = f"https://graph.facebook.com/v19.0/{self.wa_id}"
        self.message_url = self.base_url + "/messages"
        self.auth_header = {"Authorization": f"Bearer {self.api_key}"}
        self.client = requests.Session()
        self.client.headers.update(self.auth_header)

    def get_client(self) -> requests.Session:
        """
        Returns the client object with the necessary headers.
        """
        return self.client

    def send_message(
        self,
        recipient_number: str,
        message_type: str,
        type_data: dict = None,
        message_context: dict = None,
    ) -> requests.Response:
        """
        Function to send message to WhatsApp

        :param `recipient_number`: The number to which message is to be sent
        :param `message_type`: The type of message to be sent
        :param `type_data`: The data of the message
        :param `message_context`: The context of the message
        :return: Response from the API

        Refer to the official documentation for more details: [WhatsApp Documentation](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages)
        """
        data = {
            "messaging_product": "whatsapp",
            "to": recipient_number,
            "type": message_type,
        }
        data[message_type] = type_data
        if message_context:
            data["context"] = message_context

        response = self.client.post(self.message_url, json=data)
        return response
