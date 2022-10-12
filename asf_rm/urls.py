"""asf_rm URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path
import core.views as cv
from django.contrib.auth import views as auth_views
from django.contrib import admin
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('core/', include('core.urls')),
    path('back-office/', include('back_office.urls')),
    path('library/', include('library.urls')),
    path('accounts/login/', cv.UserLogin.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), {'next_page': '/'}, name='logout'),
    path('search/', cv.SearchResults.as_view(), name='search'),
    path('', login_required(cv.AnalysisListView.as_view()), name='home'),
    path('staff/x-rays', login_required(cv.ReviewView.as_view()), name='xrays'),

    path("__reload__/", include("django_browser_reload.urls")),
]
