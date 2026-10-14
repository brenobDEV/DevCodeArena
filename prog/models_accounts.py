"""Perfil de conta do DevCodeArena (desenvolvedor ou empresa)."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    DEVELOPER = "developer"
    COMPANY = "company"
    TIPOS = [(DEVELOPER, "Desenvolvedor"), (COMPANY, "Empresa")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dca_profile"
    )
    tipo = models.CharField(max_length=10, choices=TIPOS, default=DEVELOPER)
    cpf = models.CharField(max_length=11, unique=True)  # Dado pessoal: não exibir publicamente.
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.public_name} ({self.get_tipo_display()})"

    @property
    def public_name(self):
        """Nome público sem expor username/e-mail quando o nome não foi informado."""
        full_name = self.user.get_full_name().strip()
        return full_name or f"{'Dev' if self.tipo == self.DEVELOPER else 'Empresa'} #{self.pk}"
