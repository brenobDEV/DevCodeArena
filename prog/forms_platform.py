from django import forms

from .models import Challenge, Message, Submission


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field__input")


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
            "start_at": "Deixe vazio para iniciar assim que for publicado.",
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
