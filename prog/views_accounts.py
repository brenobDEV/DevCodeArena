from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from .forms_accounts import LoginForm, SignupForm
from .models_accounts import Profile
#-------------------------------------tony :>---------------------------------------------
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
#-------------------------------------tony :>---------------------------------------------

COPY = {
    Profile.DEVELOPER: {
        "slug": "dev", "glyph": "</>", "badge": "Para desenvolvedores",
        "login_title": "Entre e deixe seu código falar.", "login_text": "Acesse seus desafios, envie soluções e acompanhe as oportunidades.",
        "signup_title": "Crie sua conta de desenvolvedor.", "signup_text": "Resolva desafios inspirados em problemas reais e apresente suas habilidades às empresas.",
    },
    Profile.COMPANY: {
        "slug": "empresa", "glyph": "{ }", "badge": "Para empresas",
        "login_title": "Encontre talentos pelo que eles entregam.", "login_text": "Gerencie desafios, avalie soluções e converse com quem se destacou.",
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


def login_choose(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "accounts/login_choose.html", {"next": _safe_next(request)})


def _signup(request, kind):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None, kind=kind)
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




#-------------------------------------tony :>---------------------------------------------

from .forms import (
    PerfilForm,
    PerfilDesenvolvedorForm,
    PerfilEmpresaForm,
    ProjetoPortfolioForm,
)
from .models import (
    Perfil,
    PerfilDesenvolvedor,
    PerfilEmpresa,
    PerfilFavorito,
    ProjetoPortfolio,
)
from .services import excluir_projeto


def listar_perfis(request):
    perfis = Perfil.objects.filter(publico=True).select_related("usuario")
    tipo = request.GET.get("tipo", "").strip()
    busca = request.GET.get("q", "").strip()

    if tipo in Perfil.Tipo.values:
        perfis = perfis.filter(tipo=tipo)

    if busca:
        perfis = perfis.filter(
            Q(nome_publico__icontains=busca)
            | Q(biografia__icontains=busca)
            | Q(desenvolvedor__especialidade__icontains=busca)
            | Q(empresa__nome_empresa__icontains=busca)
            | Q(empresa__setor__icontains=busca)
        ).distinct()

    return render(
        request,
        "perfis/listar.html",
        {"perfis": perfis, "busca": busca, "tipo": tipo},
    )


def detalhe_perfil(request, pk):
    perfil = get_object_or_404(
        Perfil.objects.select_related("usuario"), pk=pk
    )
    dono = (
        request.user.is_authenticated
        and perfil.usuario_id == request.user.pk
    )

    if not perfil.publico and not dono:
        raise Http404("Perfil não encontrado.")

    dados = {"perfil": perfil, "dono": dono}

    if perfil.tipo == Perfil.Tipo.DESENVOLVEDOR:
        dados["dados_tipo"] = PerfilDesenvolvedor.objects.filter(
            perfil=perfil
        ).first()
    else:
        dados["dados_tipo"] = PerfilEmpresa.objects.filter(
            perfil=perfil
        ).first()

    dados["projetos"] = perfil.projetos.filter(publicado=True)

    if dono:
        dados["projetos_proprios"] = perfil.projetos.all()

    if request.user.is_authenticated and not dono:
        dados["favoritado"] = PerfilFavorito.objects.filter(
            usuario=request.user, perfil=perfil
        ).exists()

    return render(request, "perfis/detalhe.html", dados)


@login_required
@transaction.atomic
def editar_perfil(request):
    perfil = get_object_or_404(
        Perfil.objects.select_for_update(), usuario=request.user
    )

    if perfil.tipo == Perfil.Tipo.DESENVOLVEDOR:
        perfil_especifico, _ = PerfilDesenvolvedor.objects.get_or_create(
            perfil=perfil
        )
        FormTipo = PerfilDesenvolvedorForm
    else:
        perfil_especifico, _ = PerfilEmpresa.objects.get_or_create(
            perfil=perfil,
            defaults={"nome_empresa": perfil.nome_publico},
        )
        FormTipo = PerfilEmpresaForm

    if request.method == "POST":
        form_perfil = PerfilForm(request.POST, instance=perfil)
        form_tipo = FormTipo(request.POST, instance=perfil_especifico)

        if form_perfil.is_valid() and form_tipo.is_valid():
            form_perfil.save()
            form_tipo.save()
            messages.success(request, "Perfil atualizado com sucesso.")
            return redirect("perfis:editar")
    else:
        form_perfil = PerfilForm(instance=perfil)
        form_tipo = FormTipo(instance=perfil_especifico)

    return render(
        request,
        "perfis/editar.html",
        {
            "perfil": perfil,
            "form_perfil": form_perfil,
            "form_tipo": form_tipo,
        },
    )


@login_required
def gerenciar_projetos(request):
    perfil = get_object_or_404(
        Perfil,
        usuario=request.user,
        tipo=Perfil.Tipo.DESENVOLVEDOR,
    )

    if request.method == "POST":
        form = ProjetoPortfolioForm(request.POST)
        if form.is_valid():
            projeto = form.save(commit=False)
            projeto.perfil = perfil
            projeto.save()
            messages.success(request, "Projeto cadastrado.")
            return redirect("perfis:projetos")
    else:
        form = ProjetoPortfolioForm()

    return render(
        request,
        "perfis/projetos.html",
        {"form": form, "projetos": perfil.projetos.all()},
    )


@login_required
def editar_projeto(request, pk):
    perfil = get_object_or_404(Perfil, usuario=request.user)
    projeto = get_object_or_404(
        ProjetoPortfolio, pk=pk, perfil=perfil
    )

    if request.method == "POST":
        form = ProjetoPortfolioForm(request.POST, instance=projeto)
        if form.is_valid():
            form.save()
            messages.success(request, "Projeto atualizado.")
            return redirect("perfis:projetos")
    else:
        form = ProjetoPortfolioForm(instance=projeto)

    return render(
        request,
        "perfis/projeto_editar.html",
        {"form": form, "projeto": projeto},
    )


@login_required
@require_POST
def excluir_projeto_view(request, pk):
    perfil = get_object_or_404(Perfil, usuario=request.user)

    try:
        excluir_projeto(perfil, pk)
    except ValidationError:
        raise Http404("Projeto não encontrado.")

    messages.success(request, "Projeto excluído.")
    return redirect("perfis:projetos")


@login_required
@require_POST
def alternar_favorito(request, pk):
    perfil = get_object_or_404(Perfil, pk=pk, publico=True)

    if perfil.usuario_id == request.user.pk:
        messages.error(request, "Você não pode favoritar seu próprio perfil.")
        return redirect(perfil.get_absolute_url())

    favorito, criado = PerfilFavorito.objects.get_or_create(
        usuario=request.user, perfil=perfil
    )

    if not criado:
        favorito.delete()
        messages.success(request, "Perfil removido dos favoritos.")
    else:
        messages.success(request, "Perfil adicionado aos favoritos.")

    return redirect(perfil.get_absolute_url())


@login_required
def meus_favoritos(request):
    favoritos = PerfilFavorito.objects.filter(
        usuario=request.user, perfil__publico=True
    ).select_related("perfil", "perfil__usuario")

    return render(
        request, "perfis/favoritos.html", {"favoritos": favoritos}
    )
#-------------------------------------tony :>---------------------------------------------