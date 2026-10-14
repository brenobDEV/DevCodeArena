from django.contrib import admin

from .models import Challenge, Conversation, Message, Participation, Submission
from .models_accounts import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "tipo", "created_at")
    search_fields = ("user__username", "user__email")
    list_filter = ("tipo", "created_at")


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
