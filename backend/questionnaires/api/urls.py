"""
URL Configuration for Questionnaires API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuestionnaireViewSet, QuestionViewSet, QuestionnaireRunViewSet

router = DefaultRouter()
router.register(r'questionnaires', QuestionnaireViewSet, basename='questionnaire')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'runs', QuestionnaireRunViewSet, basename='questionnaire-run')

urlpatterns = [
    path('', include(router.urls)),
]
