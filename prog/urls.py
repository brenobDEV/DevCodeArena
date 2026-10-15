from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("", include("prog.urls_accounts")),
    path("", include("prog.urls_platform")),
]
