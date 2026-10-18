/* DevCodeArena — home_motion.js: revelar ao rolar, inclinação do palco e fallback das cenas 3D.
   Fica fora do home.js de propósito: se o three.js não carregar, a página continua funcionando. */
const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
const revealItems = document.querySelectorAll(".home-reveal");
const heroVisual = document.querySelector(".hero-visual");

if (!motionPreference.matches) {
  if ("IntersectionObserver" in window) {
    document.documentElement.classList.add("has-motion");
    const revealObserver = new IntersectionObserver((entries, currentObserver) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        currentObserver.unobserve(entry.target);
      });
    }, { threshold: 0.12 });
    revealItems.forEach((item) => revealObserver.observe(item));

    if (heroVisual) {
      const motionObserver = new IntersectionObserver(([entry]) => {
        heroVisual.classList.toggle("is-in-view", entry.isIntersecting);
      }, { threshold: 0.05 });
      motionObserver.observe(heroVisual);
    }
  }

  const tiltStage = heroVisual?.querySelector("[data-tilt]");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  if (tiltStage && finePointer.matches) {
    let frame = 0;
    heroVisual.addEventListener("pointermove", (event) => {
      if (frame) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const bounds = heroVisual.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width * 2 - 1;
        const y = (event.clientY - bounds.top) / bounds.height * 2 - 1;
        tiltStage.style.setProperty("--tilt-x", `${-y * 5}deg`);
        tiltStage.style.setProperty("--tilt-y", `${x * 7}deg`);
        frame = 0;
      });
    }, { passive: true });
    heroVisual.addEventListener("pointerleave", () => {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      tiltStage.style.setProperty("--tilt-x", "0deg");
      tiltStage.style.setProperty("--tilt-y", "0deg");
    }, { passive: true });
  }
}

const scenes = document.querySelectorAll(".scene");
if (motionPreference.matches || navigator.connection?.saveData || !("IntersectionObserver" in window)) {
  scenes.forEach((scene) => scene.classList.add("is-fallback"));
} else if (scenes.length) {
  const sceneLoader = new IntersectionObserver((entries, observer) => {
    if (!entries.some((entry) => entry.isIntersecting)) return;
    observer.disconnect();
    import("./home.js?v=22").catch((error) => {
      scenes.forEach((scene) => scene.classList.add("is-fallback"));
      console.error("[DevCodeArena] Não foi possível carregar o módulo 3D; a versão estática será exibida.", error);
    });
  }, { rootMargin: "0px" });
  scenes.forEach((scene) => sceneLoader.observe(scene));
}

setTimeout(() => {
  scenes.forEach((scene) => {
    if (!scene.dataset.ready) scene.classList.add("is-fallback");
  });
}, 8000);
