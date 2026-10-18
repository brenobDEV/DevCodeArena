"""No prog/urls.py, acrescente:  path("", include("prog.urls_accounts")),   (import include)"""
from django.contrib.auth.views import LogoutView
from django.urls import path
from django.urls import path
from . import views

from . import views_accounts as v

urlpatterns = [
    path("entrar/", v.login_choose, name="login"),
    path("entrar/dev/", v.login_dev, name="login_dev"),
    path("entrar/empresa/", v.login_company, name="login_company"),
    path("cadastro/", v.signup_choose, name="signup"),
    path("cadastro/dev/", v.signup_dev, name="signup_dev"),
    path("cadastro/empresa/", v.signup_company, name="signup_company"),
    path("sair/", LogoutView.as_view(next_page="home"), name="logout"),   # POST (Django 5)
    path("", views.listar_perfis, name="listar"),
    path("meu-perfil/editar/", views.editar_perfil, name="editar"),
    path("meus-projetos/", views.gerenciar_projetos, name="projetos"),
    path("projetos/<int:pk>/editar/", views.editar_projeto, name="editar_projeto"),
    path("projetos/<int:pk>/excluir/", views.excluir_projeto_view, name="excluir_projeto"),
    path("favoritos/", views.meus_favoritos, name="favoritos"),
    path("<int:pk>/favoritar/", views.alternar_favorito, name="alternar_favorito"),
    path("<int:pk>/", views.detalhe_perfil, name="detalhe"),
]

#-------------------------------------tony :>---------------------------------------------
app_name = "perfis"
#-------------------------------------tony :>---------------------------------------------
