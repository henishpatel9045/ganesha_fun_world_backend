from django.views.generic import FormView
from .forms import BookingForm


class BookingFormView(FormView):
    template_name = "booking/booking.html"
    form_class = BookingForm
    success_url = "/admin"

    def form_valid(self, form):
        try:
            form = form.save()
            return super().form_valid(form)
        except Exception as e:
            return super().form_invalid(form)
            