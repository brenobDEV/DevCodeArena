"""Perfil de conta do DevCodeArena (desenvolvedor ou empresa).

Em models.py do app, acrescente UMA linha:
    from .models_accounts import Profile  # noqa: F401
Depois: python manage.py makemigrations prog && python manage.py migrate
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

class Profile(models.Model):
    DEVELOPER = "developer"
    COMPANY = "company"
    TIPOS = [(DEVELOPER, "Desenvolvedor"), (COMPANY, "Empresa")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dca_profile")
    tipo = models.CharField(max_length=10, choices=TIPOS, default="developer")
    cpf = models.CharField(max_length=11, unique=True)   # somente dígitos; dado pessoal (LGPD)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_tipo_display()})"
