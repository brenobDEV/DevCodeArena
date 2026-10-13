/* DevCodeArena — base.js: tema e modal de canais */
(function () {
  var root = document.documentElement, KEY = "dca-theme";
  var stored = null;
  try { stored = localStorage.getItem(KEY); } catch (e) {}
  var theme = stored === "dark" ? "dark" : "light";   // padrão: claro, como no protótipo

  function apply(t) {
    theme = t;
    root.dataset.theme = t;
    root.dataset.bsTheme = t;
    document.querySelectorAll("[data-theme-toggle]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(t === "dark"));
    });
    try { localStorage.setItem(KEY, t); } catch (e) {}
    document.dispatchEvent(new CustomEvent("dca:theme", { detail: t }));
  }
  root.dataset.theme = theme; root.dataset.bsTheme = theme;

  document.addEventListener("DOMContentLoaded", function () {
    apply(theme);
    document.querySelectorAll("[data-theme-toggle]").forEach(function (b) {
      b.addEventListener("click", function () { apply(theme === "dark" ? "light" : "dark"); });
    });

    var modal = document.getElementById("channel-modal");
    if (!modal) return;
    modal.addEventListener("show.bs.modal", function (ev) {
      var d = ev.relatedTarget ? ev.relatedTarget.dataset : {};
      modal.querySelector(".modal-title").textContent = d.name || "";
      modal.querySelector(".channel-modal__desc").textContent = d.desc || "";
      modal.querySelector(".channel-modal__icon").className = "bi bi-" + (d.icon || "link-45deg") + " channel-modal__icon";
      var open = modal.querySelector(".channel-modal__open"), pending = modal.querySelector(".channel-modal__pending");
      if (d.url) { open.href = d.url; open.hidden = false; pending.hidden = true; }
      else { open.removeAttribute("href"); open.hidden = true; pending.hidden = false; }
    });
  });
})();
