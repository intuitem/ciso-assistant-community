from django.urls import include, path
from rest_framework import routers

from .views import (
    ChatSessionViewSet,
    IndexedDocumentViewSet,
    QuestionnaireRunViewSet,
    QuestionnaireQuestionViewSet,
    AgentRunViewSet,
    AgentActionViewSet,
    chat_status,
    ollama_models,
)

router = routers.DefaultRouter()
router.register(r"sessions", ChatSessionViewSet, basename="chat-sessions")
router.register(r"documents", IndexedDocumentViewSet, basename="chat-documents")
router.register(
    r"questionnaire-runs", QuestionnaireRunViewSet, basename="questionnaire-runs"
)
router.register(
    r"questionnaire-questions",
    QuestionnaireQuestionViewSet,
    basename="questionnaire-questions",
)
router.register(r"agent-runs", AgentRunViewSet, basename="agent-runs")
router.register(r"agent-actions", AgentActionViewSet, basename="agent-actions")

urlpatterns = [
    path("", include(router.urls)),
    path("status/", chat_status, name="chat-status"),
    path("ollama-models/", ollama_models, name="ollama-models"),
]
