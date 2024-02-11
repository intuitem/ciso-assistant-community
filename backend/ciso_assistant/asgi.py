"""
<<<<<<<< HEAD:backend/ciso_assistant/asgi.py
ASGI config for ciso_assistant project.
========
ASGI config for mira project.
>>>>>>>> main:mira/asgi.py

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

<<<<<<<< HEAD:backend/ciso_assistant/asgi.py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
========
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mira.settings')
>>>>>>>> main:mira/asgi.py

application = get_asgi_application()
