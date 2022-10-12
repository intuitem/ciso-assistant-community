from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('packages/', login_required(views.PackageListView.as_view()), name='package-list'),
    path('packages/<str:package>/', login_required(views.PackageDetailView.as_view()), name='package-detail'),
]