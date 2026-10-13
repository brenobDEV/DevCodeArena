"""Context processor do DevCodeArena. settings.py: 'prog.context_processors.dca' em TEMPLATES[...]['context_processors']."""
from django.conf import settings
from django.urls import NoReverseMatch, reverse

URL_NAMES = {
    "home": "home", "login_dev": "login_dev", "login_company": "login_company",
    "signup": "signup", "signup_dev": "signup_dev", "signup_company": "signup_company", "logout": "logout",
    # ainda sem rota no projeto: viram "#" até você criar/ajustar os nomes
    "challenges": "challenges", "solutions": "solutions", "profile": "profile", "chats": "chats", "settings": "settings",
    "company_panel": "company_panel", "challenge_new": "challenge_new", "company_challenges": "company_challenges",
    "received_solutions": "received_solutions",
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
    """'developer', 'company' ou None (visitante). Lê o Profile; contas sem perfil (ex.: admin) caem em 'developer'."""
    if not user.is_authenticated:
        return None
    profile = getattr(user, "dca_profile", None)
    return profile.tipo if profile else "developer"


def dca(request):
    links = getattr(settings, "DCA_SOCIAL_LINKS", {})
    return {
        "nav": {key: _url(name) for key, name in URL_NAMES.items()},
        "account_type": account_type(request.user),
        "channels": [{**c, "url": links.get(c["key"], "")} for c in CHANNELS],
    }
