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


def normalize_cnpj(value):
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def valid_cnpj(cnpj):
    cnpj = normalize_cnpj(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14 or not cnpj[:12].isalnum() or not cnpj[12:].isdigit():
        return False

    def check_digit(value, weights):
        total = sum((ord(char) - 48) * weight for char, weight in zip(value, weights))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first_digit = check_digit(cnpj[:12], (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    second_digit = check_digit(cnpj[:12] + first_digit, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))
    return cnpj[-2:] == first_digit + second_digit


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
    cnpj = forms.CharField(label="CNPJ", max_length=18,
                           widget=forms.TextInput(attrs={"inputmode": "text", "autocomplete": "off", "placeholder": "00.000.000/0000-00", "data-mask": "cnpj"}))
    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "voce@email.com"}))
    senha = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    senha2 = forms.CharField(label="Confirmar senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, kind=Profile.DEVELOPER, **kwargs):
        super().__init__(*args, **kwargs)
        if kind == Profile.COMPANY:
            self.fields.pop("cpf")
        else:
            self.fields.pop("cnpj")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "field__input")

    def clean_nome(self):
        return " ".join(self.cleaned_data["nome"].split())

    def clean_cpf(self):
        cpf = only_digits(self.cleaned_data["cpf"])
        if not valid_cpf(cpf):
            raise forms.ValidationError("Informe um CPF válido.")
        if Profile.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("Este CPF já está cadastrado.")
        return cpf

    def clean_cnpj(self):
        cnpj = normalize_cnpj(self.cleaned_data["cnpj"])
        if not valid_cnpj(cnpj):
            raise forms.ValidationError("Informe um CNPJ válido.")
        if Profile.objects.filter(cnpj=cnpj).exists():
            raise forms.ValidationError("Este CNPJ já está cadastrado.")
        return cnpj

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
        Profile.objects.create(user=user, tipo=kind, cpf=d.get("cpf"), cnpj=d.get("cnpj"))
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
