"""Perfil de conta do DevCodeArena (desenvolvedor ou empresa)."""
from django.conf import settings
from django.db import models
from django.utils import timezone
#-------------------------------------tony :>---------------------------------------------
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

#-------------------------------------tony :>---------------------------------------------


class Profile(models.Model):
    DEVELOPER = "developer"
    COMPANY = "company"
    TIPOS = [(DEVELOPER, "Desenvolvedor"), (COMPANY, "Empresa")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dca_profile"
    )
    tipo = models.CharField(max_length=10, choices=TIPOS, default=DEVELOPER)

    # CPF é só do desenvolvedor; CNPJ é só da empresa. O outro fica NULL
    # (NULL não conflita com unique, então várias contas podem ficar sem um deles).
    cpf = models.CharField(max_length=11, unique=True, null=True, blank=True)  # Dado pessoal: não exibir publicamente.
    cnpj = models.CharField(max_length=14, unique=True, null=True, blank=True)  # 14 caracteres (aceita CNPJ alfanumérico).

    # Endereço da empresa (preenchido via ViaCEP). Fica vazio para desenvolvedores.
    cep = models.CharField(max_length=8, blank=True)
    logradouro = models.CharField(max_length=150, blank=True)
    numero = models.CharField(max_length=10, blank=True)
    complemento = models.CharField(max_length=80, blank=True)
    bairro = models.CharField(max_length=80, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    uf = models.CharField(max_length=2, blank=True)

    bio = models.TextField(blank=True)
    skills = models.CharField(max_length=500, blank=True)
    technologies = models.CharField(max_length=500, blank=True)
    portfolio_url = models.URLField(max_length=500, blank=True)
    github_url = models.URLField(max_length=500, blank=True)
    linkedin_url = models.URLField(max_length=500, blank=True)
    website_url = models.URLField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to="profile_photos/", blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.public_name} ({self.get_tipo_display()})"

    @property
    def public_name(self):
        """Nome público sem expor username/e-mail quando o nome não foi informado."""
        full_name = self.user.get_full_name().strip()
        return full_name or f"{'Dev' if self.tipo == self.DEVELOPER else 'Empresa'} #{self.pk}"

#-------------------------------------tony :>---------------------------------------------


class Perfil(models.Model):
    class Tipo(models.TextChoices):
        DESENVOLVEDOR = "DEV", "Desenvolvedor"
        EMPRESA = "EMP", "Empresa"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_profissional",
    )
    tipo = models.CharField(max_length=3, choices=Tipo.choices)
    nome_publico = models.CharField(max_length=100)
    biografia = models.TextField(max_length=1500, blank=True)
    localizacao = models.CharField(max_length=120, blank=True)
    site = models.URLField(blank=True)
    publico = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome_publico"]

    def __str__(self):
        return f"{self.nome_publico} ({self.get_tipo_display()})"

    def get_absolute_url(self):
        return reverse("perfis:detalhe", kwargs={"pk": self.pk})


class PerfilDesenvolvedor(models.Model):
    perfil = models.OneToOneField(
        Perfil, on_delete=models.CASCADE, related_name="desenvolvedor"
    )
    especialidade = models.CharField(max_length=100, blank=True)
    experiencia_anos = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(60)]
    )
    github = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    portfolio = models.URLField(blank=True)
    disponivel_para_trabalho = models.BooleanField(default=True)

    def __str__(self):
        return f"Desenvolvedor: {self.perfil.nome_publico}"


class PerfilEmpresa(models.Model):
    perfil = models.OneToOneField(
        Perfil, on_delete=models.CASCADE, related_name="empresa"
    )
    nome_empresa = models.CharField(max_length=150)
    setor = models.CharField(max_length=100, blank=True)
    site_empresa = models.URLField(blank=True)
    descricao = models.TextField(max_length=2000, blank=True)
    contato_profissional = models.EmailField(blank=True)

    def __str__(self):
        return self.nome_empresa


class Habilidade(models.Model):
    nome = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class HabilidadePerfil(models.Model):
    perfil = models.ForeignKey(
        Perfil, on_delete=models.CASCADE, related_name="habilidades"
    )
    habilidade = models.ForeignKey(
        Habilidade, on_delete=models.CASCADE, related_name="perfis"
    )
    nivel = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["perfil", "habilidade"],
                name="unica_habilidade_por_perfil",
            )
        ]

    def __str__(self):
        return f"{self.perfil} - {self.habilidade}"


class ProjetoPortfolio(models.Model):
    perfil = models.ForeignKey(
        Perfil, on_delete=models.CASCADE, related_name="projetos"
    )
    titulo = models.CharField(max_length=120)
    descricao = models.TextField(max_length=2000)
    url_projeto = models.URLField(blank=True)
    tecnologias = models.CharField(max_length=300, blank=True)
    publicado = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo


class PerfilFavorito(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfis_favoritos",
    )
    perfil = models.ForeignKey(
        Perfil, on_delete=models.CASCADE, related_name="favoritado_por"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "perfil"],
                name="unico_favorito_por_usuario",
            )
        ]
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.usuario} -> {self.perfil}"
#-------------------------------------tony :>---------------------------------------------