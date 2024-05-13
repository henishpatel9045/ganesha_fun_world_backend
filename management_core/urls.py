from django.urls import path

from .views import TicketListPriceFormView


urlpatterns = [
    path(
        "ticket-price-list-create-bulk",
        TicketListPriceFormView.as_view(),
        name="ticket_list_price_create_bulk",
    ),
]
