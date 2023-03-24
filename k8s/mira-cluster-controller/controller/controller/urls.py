"""controller URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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

    
For simple 2FA, see: https://www.calazan.com/how-to-enable-2fa-in-the-django-admin/    

"""
from django.contrib import admin
from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView
#from . import views

from django_otp.admin import OTPAdminSite

admin.site.__class__ = OTPAdminSite
admin.site.site_header  =  "MIRA demo cluster"  
admin.site.site_title  =  "MIRA demo cluster"
admin.site.index_title  =  "Dashboard"

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('admin:index'))),
    path('admin/', admin.site.urls),
]

