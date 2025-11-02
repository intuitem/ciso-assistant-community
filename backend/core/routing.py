"""
WebSocket routing for core app.
"""

from django.urls import re_path
from core.consumers import CollabEditorConsumer

websocket_urlpatterns = [
    re_path(r"ws/collab-editor/$", CollabEditorConsumer.as_asgi()),
]
