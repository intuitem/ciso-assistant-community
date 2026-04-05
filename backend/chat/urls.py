from django.urls import include, path
from rest_framework import routers

from .views import (
    ChatSessionViewSet,
    IndexedDocumentViewSet,
    chat_status,
    ollama_models,
)

router = routers.DefaultRouter()
router.register(r"sessions", ChatSessionViewSet, basename="chat-sessions")
router.register(r"documents", IndexedDocumentViewSet, basename="chat-documents")

urlpatterns = [
    path("", include(router.urls)),
    path("status/", chat_status, name="chat-status"),
    path("ollama-models/", ollama_models, name="ollama-models"),
]
