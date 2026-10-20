from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Challenge, Message, Submission
from .models_accounts import Profile


MAX_AVATAR_SIZE = 5 * 1024 * 1024
MAX_AVATAR_DIMENSION = 4096
ALLOWED_AVATAR_FORMATS = {"JPEG", "PNG", "WEBP"}


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field__input")


class ProfileForm(StyledModelForm):
    remove_avatar = forms.BooleanField(
        label="Remover foto atual",
        required=False,
    )
    public_name = forms.CharField(
        label="Nome público", max_length=150,
        help_text="Este nome será exibido às empresas nos desafios em que você participar.",
    )
    bio = forms.CharField(
        label="Sobre você", required=False, max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    class Meta:
        model = Profile
        fields = [
            "avatar", "bio", "skills", "technologies", "portfolio_url",
            "github_url", "linkedin_url", "website_url",
        ]
        labels = {
            "bio": "Sobre você",
            "skills": "Competências",
            "technologies": "Linguagens e tecnologias",
            "portfolio_url": "Portfólio",
            "github_url": "GitHub",
            "linkedin_url": "LinkedIn",
            "website_url": "Site",
        }
        help_texts = {
            "bio": "Conte brevemente sua experiência ou o tipo de trabalho que procura.",
            "skills": "Separe as competências por vírgula, por exemplo: APIs, testes, UX.",
            "technologies": "Separe linguagens e tecnologias por vírgula.",
        }
        widgets = {
            "avatar": forms.FileInput(attrs={
                "accept": "image/jpeg,image/png,image/webp",
            }),
            "skills": forms.TextInput(attrs={"maxlength": "500"}),
            "technologies": forms.TextInput(attrs={"maxlength": "500"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_avatar_name = self.instance.avatar.name
        self._original_avatar_storage = self.instance.avatar.storage
        self.fields["avatar"].label = "Foto do perfil"
        self.fields["avatar"].help_text = "JPG, PNG ou WebP; até 5 MB e 4096 × 4096 px."
        is_company = self.instance and self.instance.tipo == Profile.COMPANY
        if is_company:
            self.fields["public_name"].help_text = "Este nome identifica sua empresa nos desafios e nas conversas."
            self.fields["bio"].label = "Sobre a empresa"
            self.fields["bio"].help_text = "Apresente brevemente sua empresa, produto ou equipe."
            self.fields["skills"].label = "Áreas de atuação"
            self.fields["skills"].help_text = "Separe por vírgulas, por exemplo: fintech, educação, saúde."
            self.fields["technologies"].label = "Tecnologias da equipe"
            self.fields["technologies"].help_text = "Quais linguagens e ferramentas sua equipe usa?"
            self.fields["portfolio_url"].label = "Portfólio ou produto"
            self.fields["website_url"].label = "Site da empresa"
        else:
            self.fields["public_name"].help_text = "Este nome será exibido às empresas nos desafios em que você participar."
            self.fields["bio"].label = "Sobre você"
            self.fields["bio"].help_text = "Conte brevemente sua experiência ou o tipo de trabalho que procura."
        self.order_fields([
            "avatar", "remove_avatar", "public_name", "bio", "skills", "technologies", "portfolio_url",
            "github_url", "linkedin_url", "website_url",
        ])
        if self.instance and self.instance.pk:
            self.fields["public_name"].initial = self.instance.public_name

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if not avatar or not self.files.get("avatar"):
            return avatar
        if avatar.size > MAX_AVATAR_SIZE:
            raise ValidationError("A foto deve ter no máximo 5 MB.")
        image = getattr(avatar, "image", None)
        image_format = getattr(image, "format", None)
        if image_format not in ALLOWED_AVATAR_FORMATS:
            raise ValidationError("Use uma imagem JPG, PNG ou WebP válida.")
        if image.width > MAX_AVATAR_DIMENSION or image.height > MAX_AVATAR_DIMENSION:
            raise ValidationError("A foto deve ter no máximo 4096 × 4096 pixels.")
        return avatar

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("remove_avatar") and self.files.get("avatar"):
            self.add_error("remove_avatar", "Escolha uma nova foto ou marque a remoção, não os dois.")
        return cleaned_data

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.cleaned_data.get("remove_avatar"):
            profile.avatar = ""
        profile.user.first_name = self.cleaned_data["public_name"]
        if commit:
            profile.save()
            profile.user.save(update_fields=["first_name"])
            if self._original_avatar_name and (
                self.files.get("avatar") or self.cleaned_data.get("remove_avatar")
            ):
                transaction.on_commit(
                    lambda: self._original_avatar_storage.delete(self._original_avatar_name)
                )
        return profile


class ChallengeForm(StyledModelForm):
    class Meta:
        model = Challenge
        fields = [
            "title", "description", "reward", "start_at", "deadline", "period",
            "difficulty", "languages", "technologies", "requirements", "evaluation_criteria",
        ]
        labels = {
            "title": "Nome do desafio",
            "description": "Descrição",
            "reward": "Recompensa (R$; opcional)",
            "start_at": "Início (opcional)",
            "deadline": "Encerramento",
            "period": "Ciclo",
            "difficulty": "Dificuldade",
            "languages": "Linguagens",
            "technologies": "Tecnologias e frameworks",
            "requirements": "Requisitos",
            "evaluation_criteria": "Critérios de avaliação",
        }
        help_texts = {
            "start_at": "Deixe vazio para aparecer assim que for publicado. Com uma data futura, o desafio só aparece para os devs a partir dela.",
            "languages": "Separe linguagens por vírgula, por exemplo: Python, JavaScript.",
            "technologies": "Separe tecnologias por vírgula, por exemplo: Django, PostgreSQL.",
            "evaluation_criteria": "Descreva como a empresa avaliará a entrega. A avaliação é manual nesta versão.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "start_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
            ),
            "deadline": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
            ),
            "requirements": forms.Textarea(attrs={"rows": 4}),
            "evaluation_criteria": forms.Textarea(attrs={"rows": 4}),
            "reward": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("start_at", "deadline"):
            self.fields[name].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]

    def clean_reward(self):
        reward = self.cleaned_data.get("reward")
        if reward is not None and reward < 0:
            raise forms.ValidationError("A recompensa não pode ser negativa.")
        return reward or 0

    def clean(self):
        cleaned = super().clean()
        start_at = cleaned.get("start_at")
        deadline = cleaned.get("deadline")
        if start_at and deadline and deadline <= start_at:
            self.add_error("deadline", "O encerramento deve acontecer depois do início.")
        return cleaned


class SubmissionForm(StyledModelForm):
    class Meta:
        model = Submission
        fields = ["repository_url", "demo_url", "notes"]
        labels = {
            "repository_url": "Link do repositório",
            "demo_url": "Demonstração (opcional)",
            "notes": "Notas para a avaliação",
        }
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}


class ReviewSubmissionForm(StyledModelForm):
    score = forms.DecimalField(
        label="Nota (0 a 100)", min_value=0, max_value=100, max_digits=5,
        decimal_places=2, widget=forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.5"}),
    )
    feedback = forms.CharField(
        label="Feedback para o desenvolvedor", required=False,
        widget=forms.Textarea(attrs={"rows": 4, "maxlength": "4000"}),
    )

    class Meta:
        model = Submission
        fields = ["score", "feedback"]


class MessageForm(forms.ModelForm):
    body = forms.CharField(
        label="Mensagem", min_length=1, max_length=4000,
        widget=forms.Textarea(attrs={
            "rows": 3, "maxlength": "4000", "class": "field__input",
            "placeholder": "Escreva uma mensagem respeitosa e objetiva…",
        }),
    )

    class Meta:
        model = Message
        fields = ["body"]

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Digite uma mensagem antes de enviar.")
        return body
