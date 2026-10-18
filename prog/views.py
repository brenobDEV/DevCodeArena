from django.conf import settings
from django.shortcuts import render

DEFAULT_CHANNELS = [
    {"name": "GitHub", "icon": "github", "key": "github", "desc": "Código-fonte e atividade do projeto."},
    {"name": "LinkedIn", "icon": "linkedin", "key": "linkedin", "desc": "Novidades da plataforma e da equipe."},
    {"name": "Instagram", "icon": "instagram", "key": "instagram", "desc": "Bastidores e comunicados."},
    {"name": "E-mail", "icon": "envelope", "key": "email", "desc": "Fale diretamente com a equipe PROG."},
]


def home(request):
    links = getattr(settings, "DCA_SOCIAL_LINKS", {})   # ex.: {"github": "https://...", "email": "mailto:..."}
    channels = [{**c, "url": links.get(c["key"], "")} for c in DEFAULT_CHANNELS]
    return render(request, "home.html", {"channels": channels})
