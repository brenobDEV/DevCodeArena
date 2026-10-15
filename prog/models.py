from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .models_accounts import Profile


class Challenge(models.Model):
    PERIOD_WEEKLY = "weekly"
    PERIOD_MONTHLY = "monthly"
    PERIOD_CHOICES = [(PERIOD_WEEKLY, "Semanal"), (PERIOD_MONTHLY, "Mensal")]

    DIFFICULTY_BEGINNER = "beginner"
    DIFFICULTY_INTERMEDIATE = "intermediate"
    DIFFICULTY_ADVANCED = "advanced"
    DIFFICULTY_CHOICES = [
        (DIFFICULTY_BEGINNER, "Iniciante"),
        (DIFFICULTY_INTERMEDIATE, "Intermediário"),
        (DIFFICULTY_ADVANCED, "Avançado"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Rascunho"),
        (STATUS_PUBLISHED, "Publicado"),
        (STATUS_CLOSED, "Encerrado"),
    ]

    company = models.ForeignKey(
        Profile, on_delete=models.CASCADE, limit_choices_to={"tipo": Profile.COMPANY},
        related_name="challenges",
    )
    title = models.CharField(max_length=140)
    description = models.TextField()
    reward = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField()
    period = models.CharField(max_length=8, choices=PERIOD_CHOICES, default=PERIOD_WEEKLY)
    difficulty = models.CharField(max_length=16, choices=DIFFICULTY_CHOICES, default=DIFFICULTY_INTERMEDIATE)
    languages = models.CharField(max_length=240, blank=True)
    technologies = models.CharField(max_length=240, blank=True)
    requirements = models.TextField(blank=True)
    evaluation_criteria = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "period", "deadline"], name="challenge_listing_idx"),
            models.Index(fields=["company", "status"], name="challenge_company_status_idx"),
        ]

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        now = timezone.now()
        return (
            self.status == self.STATUS_PUBLISHED
            and self.is_active
            and (self.start_at is None or self.start_at <= now)
            and self.deadline >= now
        )


class Participation(models.Model):
    STATUS_REGISTERED = "registered"
    STATUS_SELECTED = "selected"
    STATUS_NOT_SELECTED = "not_selected"
    STATUS_CHOICES = [
        (STATUS_REGISTERED, "Inscrito"),
        (STATUS_SELECTED, "Selecionado"),
        (STATUS_NOT_SELECTED, "Não selecionado"),
    ]

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="participations")
    developer = models.ForeignKey(
        Profile, on_delete=models.CASCADE, limit_choices_to={"tipo": Profile.DEVELOPER},
        related_name="participations",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_REGISTERED)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-joined_at"]
        constraints = [
            models.UniqueConstraint(fields=["challenge", "developer"], name="unique_challenge_developer")
        ]
        indexes = [
            models.Index(fields=["challenge", "status"], name="participation_ch_status_idx"),
            models.Index(fields=["developer", "status"], name="participation_dev_status_idx"),
        ]

    def __str__(self):
        return f"{self.developer.public_name} — {self.challenge.title}"


class Submission(models.Model):
    participation = models.OneToOneField(Participation, on_delete=models.CASCADE, related_name="submission")
    repository_url = models.URLField(max_length=500)
    demo_url = models.URLField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [models.Index(fields=["score", "submitted_at"], name="submission_score_date_idx")]

    def __str__(self):
        return f"Submissão de {self.participation.developer.public_name}: {self.participation.challenge.title}"

    @property
    def is_reviewed(self):
        return self.score is not None and self.reviewed_at is not None


class Conversation(models.Model):
    company = models.ForeignKey(
        Profile, on_delete=models.CASCADE, limit_choices_to={"tipo": Profile.COMPANY},
        related_name="company_conversations",
    )
    developer = models.ForeignKey(
        Profile, on_delete=models.CASCADE, limit_choices_to={"tipo": Profile.DEVELOPER},
        related_name="developer_conversations",
    )
    challenge = models.ForeignKey(
        Challenge, on_delete=models.SET_NULL, null=True, blank=True, related_name="conversations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "developer", "challenge"], name="unique_company_developer_challenge_chat"
            )
        ]

    def __str__(self):
        return f"{self.company.public_name} ↔ {self.developer.public_name}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="message_conversation_date_idx"),
            models.Index(fields=["conversation", "read_at"], name="message_conversation_read_idx"),
        ]

    def __str__(self):
        return f"Mensagem #{self.pk} na conversa #{self.conversation_id}"
