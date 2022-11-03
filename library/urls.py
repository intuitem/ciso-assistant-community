from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('packages/', login_required(views.PackageListView.as_view()), name='package-list'),
    path('PKG/<str:package>/', login_required(views.PackageDetailView.as_view()), name='package-detail'),

    path('import_default_package/<str:package_name>', views.import_default_package, name='import-default-package'),
]