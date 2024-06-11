from django.urls import path

from .views import (
    TicketListPriceFormView,
    LockerBulkAddFormView,
    TextOnlyPromotionalMessageFormView,
    PromotionalHomeTemplateView,
)


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
    path(
        "text-only-promotional-message",
        TextOnlyPromotionalMessageFormView.as_view(),
        name="text_only_promotional",
    ),
    path(
        "promotional-messages-home",
        PromotionalHomeTemplateView.as_view(),
        name="promotional_message_home",
    ),
]
