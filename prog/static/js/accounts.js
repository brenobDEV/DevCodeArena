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
