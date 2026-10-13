from django.urls import path
from . import views
from django.urls import path, include

urlpatterns = [
    path("", views.home, name="home"),
    path("", include("prog.urls_accounts"))
]