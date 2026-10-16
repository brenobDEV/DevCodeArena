"""No prog/urls.py, acrescente:  path("", include("prog.urls_accounts")),   (import include)"""
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views_accounts as v

urlpatterns = [
    path("entrar/", v.login_choose, name="login"),
    path("entrar/dev/", v.login_dev, name="login_dev"),
    path("entrar/empresa/", v.login_company, name="login_company"),
    path("cadastro/", v.signup_choose, name="signup"),
    path("cadastro/dev/", v.signup_dev, name="signup_dev"),
    path("cadastro/empresa/", v.signup_company, name="signup_company"),
    path("sair/", LogoutView.as_view(next_page="home"), name="logout"),   # POST (Django 5)
]
