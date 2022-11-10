from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('backup-restore/', login_required(views.BackupRestoreView.as_view()), name='backup-restore'),
    path('dump-db/', views.dump_db_view, name='dump-db'),
]