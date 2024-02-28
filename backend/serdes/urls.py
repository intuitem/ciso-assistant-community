from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path("dump-db/", login_required(views.dump_db_view), name="dump-db"),
    path(
        "load-backup/",
        login_required(views.LoadBackupView.as_view()),
        name="load-backup",
    ),
]
