"""Contexto compartilhado de navegação para o DevCodeArena."""
from django.conf import settings
from django.urls import NoReverseMatch, reverse

URL_NAMES = {
    "home": "home",
    "login_dev": "login_dev",
    "login_company": "login_company",
    "signup": "signup",
    "signup_dev": "signup_dev",
    "signup_company": "signup_company",
    "logout": "logout",
    "challenges": "challenge_periods",
    "solutions": "my_submissions",
    "profile": "account_profile",
    "chats": "conversation_list",
    "settings": "account_profile",
    "company_panel": "company_dashboard",
    "challenge_new": "company_challenge_create",
    "company_challenges": "company_challenge_management",
    "received_solutions": "company_challenge_management",
    "leaderboard": "leaderboard",
}

CHANNELS = [
    {"name": "GitHub", "icon": "github", "key": "github", "desc": "Código-fonte e atividade do projeto."},
    {"name": "LinkedIn", "icon": "linkedin", "key": "linkedin", "desc": "Novidades da plataforma e da equipe."},
    {"name": "Instagram", "icon": "instagram", "key": "instagram", "desc": "Bastidores e comunicados."},
    {"name": "E-mail", "icon": "envelope", "key": "email", "desc": "Fale diretamente com a equipe PROG."},
]


def _url(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        return "#"


def account_type(user):
    if not user.is_authenticated:
        return None
    profile = getattr(user, "dca_profile", None)
    return profile.tipo if profile else None


def dca(request):
    links = getattr(settings, "DCA_SOCIAL_LINKS", {})
    return {
        "nav": {key: _url(name) for key, name in URL_NAMES.items()},
        "account_type": account_type(request.user),
        "channels": [{**channel, "url": links.get(channel["key"], "")} for channel in CHANNELS],
    }
