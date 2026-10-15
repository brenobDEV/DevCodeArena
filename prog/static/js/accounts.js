/* DevCodeArena — accounts.js: mostrar/ocultar senha, máscaras (CPF, CNPJ, CEP) e busca de endereço no ViaCEP (a validação real é feita no servidor) */
document.querySelectorAll(".js-toggle-password").forEach((btn) => {
  btn.addEventListener("click", () => {
    const input = document.getElementById(btn.dataset.target);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.setAttribute("aria-pressed", String(show));
    btn.setAttribute("aria-label", show ? "Ocultar senha" : "Mostrar senha");
    btn.firstElementChild.className = show ? "bi bi-eye-slash" : "bi bi-eye";
  });
});

document.querySelectorAll('[data-mask="cpf"]').forEach((input) => {
  input.addEventListener("input", () => {
    const d = input.value.replace(/\D/g, "").slice(0, 11);
    input.value = d.replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  });
});

// CNPJ: 12.ABC.345/0001-DE (aceita letras nas 12 primeiras posições, formato novo da Receita)
function maskCnpj(raw) {
  const v = raw.toUpperCase().replace(/[^0-9A-Z]/g, "").slice(0, 14);
  let out = v.slice(0, 2);
  if (v.length > 2) out += "." + v.slice(2, 5);
  if (v.length > 5) out += "." + v.slice(5, 8);
  if (v.length > 8) out += "/" + v.slice(8, 12);
  if (v.length > 12) out += "-" + v.slice(12, 14);
  return out;
}

document.querySelectorAll('[data-mask="cnpj"]').forEach((input) => {
  input.addEventListener("input", () => {
    input.value = maskCnpj(input.value);
  });
});

// CEP: 00000-000 + preenchimento automático do endereço pelo ViaCEP
function maskCep(raw) {
  const d = raw.replace(/\D/g, "").slice(0, 8);
  return d.length > 5 ? d.slice(0, 5) + "-" + d.slice(5) : d;
}

// Mostra/limpa um aviso embaixo do campo de CEP (usa a mesma classe dos erros do formulário)
function cepMessage(input, text) {
  const field = input.closest(".field");
  let msg = field.querySelector(".js-cep-msg");
  if (!text) {
    if (msg) msg.remove();
    return;
  }
  if (!msg) {
    msg = document.createElement("p");
    msg.className = "field__error js-cep-msg";
    msg.setAttribute("role", "alert");
    field.appendChild(msg);
  }
  msg.textContent = text;
}

function fillAddress(data) {
  const map = { logradouro: data.logradouro, bairro: data.bairro, cidade: data.localidade, uf: data.uf };
  Object.entries(map).forEach(([name, value]) => {
    const el = document.getElementById("id_" + name);
    if (el) el.value = value || "";
  });
}

document.querySelectorAll('[data-mask="cep"]').forEach((input) => {
  input.addEventListener("input", async () => {
    input.value = maskCep(input.value);
    cepMessage(input, "");
    const cep = input.value.replace(/\D/g, "");
    if (cep.length !== 8) return;

    try {
      const res = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      if (!res.ok) throw new Error("ViaCEP indisponível");
      const data = await res.json();
      if (input.value.replace(/\D/g, "") !== cep) return; // o usuário já mudou o CEP enquanto buscava
      if (data.erro) {
        cepMessage(input, "CEP não encontrado. Preencha o endereço manualmente.");
        return;
      }
      fillAddress(data);
      const numero = document.getElementById("id_numero");
      if (numero) numero.focus(); // próximo campo que a pessoa precisa digitar
    } catch (err) {
      cepMessage(input, "Não foi possível buscar o CEP agora. Preencha o endereço manualmente.");
    }
  });
});