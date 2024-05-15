from typing import Any
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
import os
from django.conf import settings

# Create your views here.


class ReactAppTemplateView(LoginRequiredMixin, TemplateView):
    template_name = "frontend/react_app.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        BASE_DIR = settings.BASE_DIR
        print(BASE_DIR)
        js_files = []
        css_files = []
        FRONTEND_DIR = "frontend/build/assets"
        for file in os.listdir(BASE_DIR / f"staticfiles/{FRONTEND_DIR}"):
            if file.endswith(".js"):
                js_files.append(f"{FRONTEND_DIR}/{file}")
            elif file.endswith(".css"):
                css_files.append(f"{FRONTEND_DIR}/{file}")
        context = {"js_files": js_files, "css_files": css_files}
        return context
