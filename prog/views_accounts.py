from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from .forms_accounts import LoginForm, SignupForm
from .models_accounts import Profile

COPY = {
    Profile.DEVELOPER: {
        "slug": "dev", "glyph": "</>", "badge": "Para desenvolvedores",
        "login_title": "Entre e deixe seu código falar.", "login_text": "Acesse seus desafios, envie soluções e acompanhe as oportunidades.",
        "signup_title": "Crie sua conta de desenvolvedor.", "signup_text": "Resolva desafios inspirados em problemas reais. Quem avalia vê a solução, não o nome.",
    },
    Profile.COMPANY: {
        "slug": "empresa", "glyph": "{ }", "badge": "Para empresas",
        "login_title": "Encontre talentos pelo que eles entregam.", "login_text": "Gerencie desafios, avalie soluções às cegas e converse com quem se destacou.",
        "signup_title": "Crie sua conta de empresa.", "signup_text": "Publique desafios baseados em problemas reais e descubra desenvolvedores pelas soluções.",
    },
}


def _safe_next(request):
    target = request.POST.get("next") or request.GET.get("next") or ""
    ok = target and url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure())
    return target if ok else ""


def _login(request, kind):
    if request.user.is_authenticated:
        return redirect("home")
    form = LoginForm(request.POST or None, kind=kind, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        return redirect(_safe_next(request) or "home")
    return render(request, "accounts/login.html", {"form": form, "kind": kind, "copy": COPY[kind], "next": _safe_next(request)})


def _signup(request, kind):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None, kind=kind)  # kind decide se pede CPF (dev) ou CNPJ (empresa)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("home")
    return render(request, "accounts/signup.html", {"form": form, "kind": kind, "copy": COPY[kind]})


def login_dev(request): return _login(request, Profile.DEVELOPER)
def login_company(request): return _login(request, Profile.COMPANY)
def signup_dev(request): return _signup(request, Profile.DEVELOPER)
def signup_company(request): return _signup(request, Profile.COMPANY)


def signup_choose(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "accounts/signup.html", {"kind": None, "copy": None})