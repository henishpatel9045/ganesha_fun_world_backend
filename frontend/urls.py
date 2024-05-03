from django.urls import path

from .views import ReactAppTemplateView


urlpatterns = [
    path("", ReactAppTemplateView.as_view(), name="react_app"),
]
