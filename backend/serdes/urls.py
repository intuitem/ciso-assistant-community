from django.urls import path

from . import views

urlpatterns = [
    path("dump-db/", views.ExportBackupView.as_view(), name="dump-db"),
    path(
        "load-backup/",
        views.LoadBackupView.as_view(),
        name="load-backup",
    ),
]
