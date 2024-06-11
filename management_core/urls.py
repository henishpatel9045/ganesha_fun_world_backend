from django.urls import path

from .views import TicketListPriceFormView, LockerBulkAddFormView


urlpatterns = [
    path(
        "ticket-price-list-create-bulk",
        TicketListPriceFormView.as_view(),
        name="ticket_list_price_create_bulk",
    ),
    path(
        "locker-create-bulk",
        LockerBulkAddFormView.as_view(),
        name="locker_create_bulk",
    ),
]
