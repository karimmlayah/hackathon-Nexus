"""
Setup Django for the project
"""
import os
import sys
import django
from django.conf import settings

# Add the rag_app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(os.path.dirname(__file__), 'db.sqlite3'),
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'rag_app',
        ],
        SECRET_KEY='django-insecure-your-secret-key-here',
        USE_TZ=True,
    )

django.setup()

if __name__ == '__main__':
    import django.core.management
    django.core.management.execute_from_command_line()
