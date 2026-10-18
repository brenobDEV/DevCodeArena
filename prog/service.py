
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    Perfil,
    PerfilDesenvolvedor,
    PerfilEmpresa,
    ProjetoPortfolio,
)


@transaction.atomic
def criar_perfil(usuario, tipo, nome_publico, nome_empresa=""):
    if tipo not in Perfil.Tipo.values:
        raise ValidationError("Tipo de perfil inválido.")

    if Perfil.objects.filter(usuario=usuario).exists():
        raise ValidationError("Este usuário já possui um perfil.")

    nome_publico = nome_publico.strip()
    nome_empresa = nome_empresa.strip()

    if not nome_publico:
        raise ValidationError("Informe um nome público.")

    if tipo == Perfil.Tipo.EMPRESA and not nome_empresa:
        raise ValidationError("Informe o nome da empresa.")

    perfil = Perfil.objects.create(
        usuario=usuario,
        tipo=tipo,
        nome_publico=nome_publico,
    )

    if tipo == Perfil.Tipo.DESENVOLVEDOR:
        PerfilDesenvolvedor.objects.create(perfil=perfil)
    else:
        PerfilEmpresa.objects.create(
            perfil=perfil,
            nome_empresa=nome_empresa,
        )

    return perfil


@transaction.atomic
def salvar_projeto(perfil, dados, projeto_id=None):
    campos_permitidos = {
        "titulo",
        "descricao",
        "url_projeto",
        "tecnologias",
        "publicado",
    }

    if projeto_id is None:
        projeto = ProjetoPortfolio(perfil=perfil)
    else:
        projeto = ProjetoPortfolio.objects.select_for_update().filter(
            pk=projeto_id, perfil=perfil
        ).first()

        if projeto is None:
            raise ValidationError("Projeto não encontrado neste perfil.")

    for campo, valor in dados.items():
        if campo in campos_permitidos:
            setattr(projeto, campo, valor)

    projeto.full_clean()
    projeto.save()
    return projeto


@transaction.atomic
def excluir_projeto(perfil, projeto_id):
    projeto = ProjetoPortfolio.objects.select_for_update().filter(
        pk=projeto_id, perfil=perfil
    ).first()

    if projeto is None:
        raise ValidationError("Projeto não encontrado neste perfil.")

    projeto.delete()
