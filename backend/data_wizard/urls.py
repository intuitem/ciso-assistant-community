from django.urls import path

from . import views

urlpatterns = [
    path(
        "load-file/",
        views.LoadFileView.as_view(),
        name="load-file",
    ),
]
