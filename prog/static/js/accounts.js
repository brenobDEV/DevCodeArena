/* DevCodeArena — accounts.js: mostrar/ocultar senha e máscara de CPF (a validação real é feita no servidor) */
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

document.querySelectorAll('[data-mask="cnpj"]').forEach((input) => {
  input.addEventListener("input", () => {
    const value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 14);
    const parts = [value.slice(0, 2), value.slice(2, 5), value.slice(5, 8), value.slice(8, 12), value.slice(12, 14)];
    input.value = parts[0]
      + (parts[1] ? `.${parts[1]}` : "")
      + (parts[2] ? `.${parts[2]}` : "")
      + (parts[3] ? `/${parts[3]}` : "")
      + (parts[4] ? `-${parts[4]}` : "");
  });
});
