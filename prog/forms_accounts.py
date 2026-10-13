import re

from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.db import transaction

from .models_accounts import Profile

User = get_user_model()
LABEL = {Profile.DEVELOPER: "desenvolvedor", Profile.COMPANY: "empresa"}


def only_digits(value):
    return re.sub(r"\D", "", value or "")


def valid_cpf(cpf):
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for n in (9, 10):
        total = sum(int(cpf[i]) * (n + 1 - i) for i in range(n))
        if (total * 10) % 11 % 10 != int(cpf[n]):
            return False
    return True


class StyledForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field__input")


class SignupForm(StyledForm):
    nome = forms.CharField(label="Nome completo", min_length=3, max_length=150,
                           widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Seu nome completo"}))
    cpf = forms.CharField(label="CPF", max_length=14,
                          widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off", "placeholder": "000.000.000-00", "data-mask": "cpf"}))
    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "voce@email.com"}))
    senha = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    senha2 = forms.CharField(label="Confirmar senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean_nome(self):
        return " ".join(self.cleaned_data["nome"].split())

    def clean_cpf(self):
        cpf = only_digits(self.cleaned_data["cpf"])
        if not valid_cpf(cpf):
            raise forms.ValidationError("Informe um CPF válido.")
        if Profile.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("Este CPF já está cadastrado.")
        return cpf

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean(self):
        data = super().clean()
        s1, s2 = data.get("senha"), data.get("senha2")
        if s1 and s2 and s1 != s2:
            self.add_error("senha2", "As senhas não coincidem.")
        elif s1:
            try:
                password_validation.validate_password(s1, User(username=data.get("email", ""), email=data.get("email", ""), first_name=data.get("nome", "")))
            except forms.ValidationError as exc:
                self.add_error("senha", exc)
        return data

    @transaction.atomic
    def save(self, kind):
        d = self.cleaned_data
        user = User.objects.create_user(username=d["email"], email=d["email"], password=d["senha"], first_name=d["nome"][:150])
        Profile.objects.create(user=user, tipo=kind, cpf=d["cpf"])
        return user


class LoginForm(StyledForm):
    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "voce@email.com"}))
    senha = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    def __init__(self, *args, kind, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind, self.request, self.user = kind, request, None

    def clean(self):
        data = super().clean()
        if not (data.get("email") and data.get("senha")):
            return data
        user = authenticate(self.request, username=data["email"].strip().lower(), password=data["senha"])
        if user is None:
            raise forms.ValidationError("E-mail ou senha incorretos.")
        profile = getattr(user, "dca_profile", None)
        if profile is not None and profile.tipo != self.kind:
            raise forms.ValidationError(f"Esta é uma conta de {LABEL[profile.tipo]}. Use o login de {LABEL[profile.tipo]}.")
        self.user = user
        return data
