from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import TemplateView
from django.views.static import serve as static_serve

from .views import qdrant_health

def _theme_root() -> Path:
    return Path(getattr(settings, "THEME_DIR"))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("qdrant/health/", qdrant_health, name="qdrant_health"),
    # Pages from the HTML template folder
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("shop.html", TemplateView.as_view(template_name="shop.html"), name="shop"),
    path("single.html", TemplateView.as_view(template_name="single.html"), name="single"),
    path("bestseller.html", TemplateView.as_view(template_name="bestseller.html"), name="bestseller"),
    path("cart.html", TemplateView.as_view(template_name="cart.html"), name="cart"),
    path("cheackout.html", TemplateView.as_view(template_name="cheackout.html"), name="cheackout"),
    path("contact.html", TemplateView.as_view(template_name="contact.html"), name="contact"),
    path("404.html", TemplateView.as_view(template_name="404.html"), name="not_found"),
]

# Dev-only: serve template assets exactly as the HTML expects (css/, js/, img/, lib/, etc.)
if settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^(?P<path>(?:css|js|img|lib|scss)/.*)$",
            static_serve,
            {"document_root": str(_theme_root())},
        ),
        # Any single file at the theme root (e.g. electronics-website-template.jpg)
        re_path(
            r"^(?P<path>[^/]+\.(?:jpg|jpeg|png|gif|webp|svg|ico|txt|md))$",
            static_serve,
            {"document_root": str(_theme_root())},
        ),
    ]

