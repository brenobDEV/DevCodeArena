import re


from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.db import transaction

from .models_accounts import Profile

User = get_user_model()
LABEL = {Profile.DEVELOPER: "desenvolvedor", Profile.COMPANY: "empresa"}

# Campos de endereço: só aparecem no cadastro de empresa.
ADDRESS_FIELDS = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")
UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


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


def only_alnum(value):
    """Mantém só letras e números (maiúsculos)."""
    return re.sub(r"[^0-9A-Za-z]", "", value or "").upper()


def _cnpj_dv(base):
    """Dígito verificador (módulo 11). Valor do caractere = ASCII - 48."""
    total = 0
    for i, ch in enumerate(reversed(base)):
        total += (ord(ch) - 48) * (2 + i % 8)  # pesos 2..9, da direita p/ esquerda
    rest = total % 11
    return "0" if rest < 2 else str(11 - rest)


def valid_cnpj(cnpj):
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", cnpj) or cnpj == cnpj[0] * 14:
        return False
    dv1 = _cnpj_dv(cnpj[:12])
    dv2 = _cnpj_dv(cnpj[:12] + dv1)
    return cnpj[12:] == dv1 + dv2


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
                           error_messages={"required": "Por favor, informe o CNPJ da empresa."},
                           widget=forms.TextInput(attrs={"autocomplete": "off", "placeholder": "00.000.000/0000-00", "data-mask": "cnpj"}))

    # --- Endereço da empresa (CEP busca o resto pelo ViaCEP no navegador) ---
    cep = forms.CharField(label="CEP", max_length=9,
                          error_messages={"required": "Por favor, informe o CEP da empresa."},
                          widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "postal-code", "placeholder": "00000-000", "data-mask": "cep"}))
    logradouro = forms.CharField(label="Rua / Avenida", max_length=150,
                                 error_messages={"required": "Informe a rua ou avenida."},
                                 widget=forms.TextInput(attrs={"autocomplete": "address-line1"}))
    numero = forms.CharField(label="Número", max_length=10,
                             error_messages={"required": "Informe o número."},
                             widget=forms.TextInput(attrs={"autocomplete": "off", "placeholder": "Ex.: 123"}))
    complemento = forms.CharField(label="Complemento (opcional)", max_length=80, required=False,
                                  widget=forms.TextInput(attrs={"autocomplete": "address-line2"}))
    bairro = forms.CharField(label="Bairro", max_length=80,
                             error_messages={"required": "Informe o bairro."})
    cidade = forms.CharField(label="Cidade", max_length=80,
                             error_messages={"required": "Informe a cidade."},
                             widget=forms.TextInput(attrs={"autocomplete": "address-level2"}))
    uf = forms.CharField(label="UF", max_length=2,
                         error_messages={"required": "Informe a UF."},
                         widget=forms.TextInput(attrs={"autocomplete": "address-level1", "placeholder": "SP", "maxlength": "2"}))

    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "voce@email.com"}))
    senha = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    senha2 = forms.CharField(label="Confirmar senha", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def __init__(self, *args, kind=Profile.DEVELOPER, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = kind
        # Cada tipo de conta mostra (e valida) só o que é dela.
        if kind == Profile.COMPANY:
            del self.fields["cpf"]   # empresa não tem CPF
            # Empresa informa o nome da empresa, não o nome de uma pessoa.
            self.fields["nome"].label = "Nome da empresa"
            self.fields["nome"].widget.attrs.update({
                "placeholder": "Nome da sua empresa",
                "autocomplete": "organization",
            })
        else:
            del self.fields["cnpj"]  # dev não tem CNPJ
            for name in ADDRESS_FIELDS:  # dev não informa endereço
                del self.fields[name]

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
        cnpj = only_alnum(self.cleaned_data["cnpj"])
        if not valid_cnpj(cnpj):
            raise forms.ValidationError("Informe um CNPJ válido.")
        if Profile.objects.filter(cnpj=cnpj).exists():
            raise forms.ValidationError("Este CNPJ já está cadastrado.")
        return cnpj

    def clean_cep(self):
        cep = only_digits(self.cleaned_data["cep"])
        if len(cep) != 8:
            raise forms.ValidationError("Informe um CEP válido (8 números).")
        return cep

    def clean_uf(self):
        uf = self.cleaned_data["uf"].strip().upper()
        if uf not in UFS:
            raise forms.ValidationError("Informe uma UF válida (ex.: SP).")
        return uf

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
    def save(self, kind=None):
        kind = kind or self.kind
        d = self.cleaned_data
        user = User.objects.create_user(username=d["email"], email=d["email"], password=d["senha"], first_name=d["nome"][:150])
        address = {name: d.get(name, "").strip() for name in ADDRESS_FIELDS}
        Profile.objects.create(user=user, tipo=kind, cpf=d.get("cpf"), cnpj=d.get("cnpj"), **address)
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