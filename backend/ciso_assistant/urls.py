"""ciso_assistant URL Configuration

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

from ciso_assistant import settings

# beware of the order of url patterns, this can change de behavior in case of multiple matches and avoid giving identical paths that could cause conflicts
urlpatterns = [
    path("api/", include("core.urls")),
    path("serdes/", include("serdes.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
]
