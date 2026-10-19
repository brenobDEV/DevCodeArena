from django.urls import path

from . import views_platform as views

urlpatterns = [
    path("desafios/ciclos/", views.challenge_periods, name="challenge_periods"),
    path("desafios/", views.challenge_list, name="challenge_list"),
    path("desafios/<int:challenge_id>/", views.challenge_detail, name="challenge_detail"),
    path("desafios/<int:challenge_id>/inscricao/", views.challenge_join, name="challenge_join"),
    path("desafios/<int:challenge_id>/submissao/", views.challenge_submit, name="challenge_submit"),
    path("minhas-solucoes/", views.developer_submissions, name="my_submissions"),
    path("conta/", views.account_profile, name="account_profile"),
    path("ranking/", views.leaderboard, name="leaderboard"),
    path("conversas/", views.conversation_list, name="conversation_list"),
    path("conversas/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
    path("empresa/", views.company_dashboard, name="company_dashboard"),
    path("empresa/desafios/", views.company_challenge_management, name="company_challenge_management"),
    path("empresa/desafios/novo/", views.company_challenge_create, name="company_challenge_create"),
    path("empresa/desafios/<int:challenge_id>/editar/", views.company_challenge_edit, name="company_challenge_edit"),
    path("empresa/desafios/<int:challenge_id>/gerenciar/", views.company_challenge_manage, name="company_challenge_manage"),
    path("empresa/desafios/<int:challenge_id>/publicacao/", views.company_challenge_toggle, name="company_challenge_toggle"),
    path("empresa/participacoes/<int:participation_id>/selecionar/", views.company_select_developer, name="company_select_developer"),
    path("empresa/submissoes/<int:submission_id>/avaliar/", views.company_review_submission, name="company_review_submission"),
]
