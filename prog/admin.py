from django.contrib import admin

from .models import Challenge, Conversation, Message, Participation, Submission
from .models_accounts import Profile
#-------------------------------------tony :>---------------------------------------------
from django.contrib import admin
from .models import (
    Perfil,
    PerfilDesenvolvedor,
    PerfilEmpresa,
    Habilidade,
    HabilidadePerfil,
    ProjetoPortfolio,
    PerfilFavorito,
)
#-------------------------------------tony :>---------------------------------------------
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "tipo", "cnpj", "cidade", "uf", "created_at")
    search_fields = ("user__username", "user__email", "cnpj", "cpf", "cidade")
    list_filter = ("tipo", "uf", "created_at")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "period", "difficulty", "status", "deadline", "created_at")
    search_fields = ("title", "description", "languages", "technologies")
    list_filter = ("status", "period", "difficulty", "created_at", "deadline")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ("challenge", "developer", "status", "joined_at")
    search_fields = ("challenge__title", "developer__user__first_name")
    list_filter = ("status", "joined_at")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("participation", "score", "submitted_at", "reviewed_at")
    search_fields = ("participation__challenge__title", "participation__developer__user__first_name")
    list_filter = ("reviewed_at", "submitted_at")
    readonly_fields = ("submitted_at", "updated_at")


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "body", "created_at", "read_at")
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("company", "developer", "challenge", "updated_at")
    list_filter = ("updated_at",)
    inlines = [MessageInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "created_at", "read_at")
    search_fields = ("body", "sender__user__first_name")
    list_filter = ("created_at", "read_at")


#-------------------------------------tony :>---------------------------------------------


class PerfilDesenvolvedorInline(admin.StackedInline):
    model = PerfilDesenvolvedor
    extra = 0


class PerfilEmpresaInline(admin.StackedInline):
    model = PerfilEmpresa
    extra = 0


class HabilidadePerfilInline(admin.TabularInline):
    model = HabilidadePerfil
    extra = 0


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("nome_publico", "tipo", "usuario", "publico")
    list_filter = ("tipo", "publico")
    search_fields = ("nome_publico", "usuario__username")
    inlines = [
        PerfilDesenvolvedorInline,
        PerfilEmpresaInline,
        HabilidadePerfilInline,
    ]


@admin.register(Habilidade)
class HabilidadeAdmin(admin.ModelAdmin):
    search_fields = ("nome",)


@admin.register(ProjetoPortfolio)
class ProjetoPortfolioAdmin(admin.ModelAdmin):
    list_display = ("titulo", "perfil", "publicado", "criado_em")
    list_filter = ("publicado",)
    search_fields = ("titulo", "perfil__nome_publico")


@admin.register(PerfilFavorito)
class PerfilFavoritoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "perfil", "criado_em")


admin.site.register(HabilidadePerfil)
#-------------------------------------tony :>---------------------------------------------