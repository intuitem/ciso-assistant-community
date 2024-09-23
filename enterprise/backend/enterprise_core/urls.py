from django.urls import include, path


from .views import get_build

urlpatterns = [
    path("build/", get_build, name="get_build"),
]
