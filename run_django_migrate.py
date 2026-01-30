"""
Run Django migrations for the database used by app.py (auth, cart, register).
Uses the same config as app.py: rag_app.db, django.contrib.auth, rag_app.
Run once from project root: python run_django_migrate.py
"""
import os
import sys

# Project root = directory containing this script
_parent = os.path.dirname(os.path.abspath(__file__))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

import django
from django.conf import settings

# Same config as app.py so we use rag_app.db
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(_parent, "rag_app.db"),
            }
        },
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "rag_app",
        ],
        SECRET_KEY="django-insecure-rag-app-cart-favorites",
        USE_TZ=True,
    )

django.setup()

from django.core.management import call_command

if __name__ == "__main__":
    print("Running Django migrations on rag_app.db...")
    call_command("migrate", verbosity=2)
    print("Done. auth_user and other tables are ready.")
