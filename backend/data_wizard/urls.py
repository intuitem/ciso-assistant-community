from django.urls import path

from . import views

urlpatterns = [
    path(
        "load-file/",
        views.LoadFileView.as_view(),
        name="load-file",
    ),
    path(
        "templates/<str:model_type>/",
        views.ImportTemplateView.as_view(),
        name="import-template",
    ),
]
