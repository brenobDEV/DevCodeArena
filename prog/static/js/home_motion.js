/* DevCodeArena — home_motion.js: revelar ao rolar e fallback das cenas 3D.
   Fica fora do home.js de propósito: se o three.js não carregar, a página continua funcionando. */
const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
const motionOverride = new URLSearchParams(window.location.search).get("motion") === "on";
const motionEnabled = !motionPreference.matches || motionOverride;
if (motionOverride) document.documentElement.classList.add("motion-override");
const revealItems = document.querySelectorAll(".home-reveal");

if (motionEnabled) {
  if ("IntersectionObserver" in window) {
    document.documentElement.classList.add("has-motion");
    const revealObserver = new IntersectionObserver((entries, currentObserver) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        currentObserver.unobserve(entry.target);
      });
    // rootMargin positivo embaixo: o bloco é revelado um pouco ANTES de entrar na tela, então já está pronto quando a pessoa chega nele
    }, { threshold: 0, rootMargin: "0px 0px 20% 0px" });
    revealItems.forEach((item) => revealObserver.observe(item));

  }
}

const scenes = document.querySelectorAll(".scene");
if ((!motionEnabled && !motionOverride) || navigator.connection?.saveData || !("IntersectionObserver" in window)) {
  scenes.forEach((scene) => scene.classList.add("is-fallback"));
} else if (scenes.length) {
  // O módulo 3D carrega já (a cena do hero começa sozinha); cada cena decide quando iniciar.
  import("./home.js?v=26").catch((error) => {
    scenes.forEach((scene) => scene.classList.add("is-fallback"));
    console.error("[DevCodeArena] Não foi possível carregar o módulo 3D; a versão estática será exibida.", error);
  });
}

setTimeout(() => {
  scenes.forEach((scene) => {
    if (!scene.dataset.ready) scene.classList.add("is-fallback");
  });
}, 8000);
