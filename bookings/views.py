from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
import requests


# Create your views here.
@csrf_exempt
def whatsapp_handler(request: HttpRequest):
    url = "https://graph.facebook.com/v19.0/285776191286365/messages"
    headers = {
        "Authorization": "Bearer EAAGuKjgErkMBO4oKP5fJSILmpFicyTp39h2VJDF4sgKcDMlpdIOHTfAbcSjEyVJqRwYctN5BhXtM46BlcR33q5YXIUalHJUoPr3GU8v1b53iGKcc9B7TUBEVOg1WkP14BhZAlffnKJUPZBwySOoZCP68tGfQRelIW2Pt75ejkZBZA3kZAwoUJb5dc6pvJOCG1IuyJgwCl52D7gp2RMfy8ZD"
    }
    number = request.GET.get("number")
    secret = request.GET.get("secret")
    if secret != "secret9045":
        return HttpResponse("Gone, world. You're at the bookings index.")
    print(number)
    payload = {
        "messaging_product": "whatsapp",
        "to": "917990577979",
        "type": "template",
        "template": {
            "name": "welcome_action",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": "image",
                            "image": {
                                "link": "https://www.shreeganeshafunworld.com/images/logo.png"
                            },
                        }
                    ],
                },
            ],
        },
    }
    res = requests.post(url, headers=headers, json=payload)
    print(res.json())

    return HttpResponse("Hello, world. You're at the bookings index.")
