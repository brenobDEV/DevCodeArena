from django.contrib import admin
from .models import Challenge
from .models_accounts import Profile

# Registrando o modelo Profile (Contas/Perfis)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tipo', 'cpf', 'created_at')
    search_fields = ('user__username', 'user__email', 'cpf')
    list_filter = ('tipo', 'created_at')

# Registrando o modelo Challenge (Desafios)
@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'reward', 'deadline', 'is_active', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('is_active', 'created_at', 'deadline')