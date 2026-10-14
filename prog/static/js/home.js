/* DevCodeArena — home.js: cena da mão + </> e Coliseu 3D (Three.js + GSAP) */
/* Os módulos 3D são baixados sob demanda para não bloquear a primeira renderização. */
let THREE;
let GLTFLoader;
let RoomEnvironment;
let mergeGeometries;
let threeModulesPromise;

function loadThreeModules() {
  if (!threeModulesPromise) {
    threeModulesPromise = Promise.all([
      import("three"),
      import("three/addons/loaders/GLTFLoader.js"),
      import("three/addons/environments/RoomEnvironment.js"),
      import("three/addons/utils/BufferGeometryUtils.js"),
    ]).then(([three, gltf, environment, geometryUtils]) => {
      THREE = three;
      GLTFLoader = gltf.GLTFLoader;
      RoomEnvironment = environment.RoomEnvironment;
      mergeGeometries = geometryUtils.mergeGeometries;
    });
  }
  return threeModulesPromise;
}

const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
addEventListener("pointermove", (e) => {
  pointer.tx = (e.clientX / innerWidth) * 2 - 1;
  pointer.ty = (e.clientY / innerHeight) * 2 - 1;
}, { passive: true });

/* ---------- Palco genérico: renderer, câmera, resize, pausa fora da tela ---------- */
function createStage(el, { fov, pos, look, exposure = 1.05, environment = true }) {
  const canvas = el.querySelector("canvas");
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, powerPreference: "high-performance" });
  } catch (err) { el.classList.add("is-fallback"); return null; }

  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = exposure;
  // Sombras dinâmicas são caras para uma landing page e não são essenciais aqui.
  renderer.shadowMap.enabled = false;

  const scene = new THREE.Scene();
  let pmrem = null;
  let envRT = null;
  if (environment) {
    pmrem = new THREE.PMREMGenerator(renderer);
    envRT = pmrem.fromScene(new RoomEnvironment(), 0.04);
    scene.environment = envRT.texture;
    scene.environmentIntensity = 0.55;
  } else {
    scene.add(new THREE.HemisphereLight(0xbfdcff, 0x0b1426, 2.0));
  }

  const camera = new THREE.PerspectiveCamera(fov, 1, 0.1, 100);
  camera.position.copy(pos);
  const clock = new THREE.Clock();
  const stage = { scene, camera, renderer, onFrame: () => {}, look: look.clone() };
  let raf = 0, visible = false, lastFrame = 0;

  const draw = () => {
    stage.onFrame(clock.getElapsedTime(), Math.min(clock.getDelta(), 0.05));
    camera.lookAt(stage.look);
    renderer.render(scene, camera);
  };
  // Limita a 30 FPS: reduz consumo de CPU/GPU mantendo as animações fluidas.
  const loop = (now) => {
    if (now - lastFrame >= 1000 / 30) {
      lastFrame = now;
      draw();
    }
    raf = requestAnimationFrame(loop);
  };
  const sync = () => {
    cancelAnimationFrame(raf);
    if (reduceMotion) { draw(); return; }
    if (visible && !document.hidden) {
      clock.getDelta();
      lastFrame = 0;
      raf = requestAnimationFrame(loop);
    }
  };
  const resize = () => {
    const w = el.clientWidth, h = el.clientHeight;
    if (!w || !h) return;
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, w < 520 ? 1 : 1.35));
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.fov = fov * (camera.aspect < 0.9 ? 1.25 : 1);
    camera.updateProjectionMatrix();
    if (reduceMotion) draw();
  };

  new ResizeObserver(resize).observe(el);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; sync(); }, { threshold: 0.01 }).observe(el);
  document.addEventListener("visibilitychange", sync);
  addEventListener("pagehide", () => {
    cancelAnimationFrame(raf);
    scene.traverse((o) => { o.geometry?.dispose(); [].concat(o.material || []).forEach((m) => m.dispose()); });
    if (envRT) envRT.dispose();
    if (pmrem) pmrem.dispose();
    renderer.dispose();
  });
  resize();
  return stage;
}

/* ---------- Símbolo </> futurista: volume escuro + arquitetura em arestas luminosas ---------- */
function buildCodeSymbol() {
  const group = new THREE.Group();
  const T = 0.34, H = 1.0, W = 0.8, DEPTH = 0.36;
  const poly = (pts) => { const s = new THREE.Shape(); pts.forEach(([x, y], i) => (i ? s.lineTo(x, y) : s.moveTo(x, y))); s.closePath(); return s; };
  const shapes = {
    right: poly([[0, H], [T, H], [T + W, 0], [T, -H], [0, -H], [W, 0]]),
    left: poly([[0, H], [-T, H], [-T - W, 0], [-T, -H], [0, -H], [-W, 0]]),
    slash: poly([[0, -1.15], [0.32, -1.15], [0.82, 1.15], [0.5, 1.15]]),
  };
  const place = { left: -0.9, slash: -0.41, right: 0.9 };
  const body = techMaterial(PALETTE.light.sym); body.transparent = true;
  body.polygonOffset = true; body.polygonOffsetFactor = 1; body.polygonOffsetUnits = 1;   // arestas por cima do volume
  const lineMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.95 });
  const gridMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.3 });
  const c1 = new THREE.Color(0x2563eb), c2 = new THREE.Color(0x00e5ff), tmp = new THREE.Color();
  for (const key of Object.keys(shapes)) {
    const geo = new THREE.ExtrudeGeometry(shapes[key], { depth: DEPTH, bevelEnabled: false });
    geo.translate(0, 0, -DEPTH / 2);
    const mesh = new THREE.Mesh(geo, body);
    mesh.position.x = place[key]; mesh.castShadow = true;
    const edges = new THREE.EdgesGeometry(geo, 20), pa = edges.getAttribute("position");
    const col = new Float32Array(pa.count * 3);
    for (let i = 0; i < pa.count; i++) { tmp.lerpColors(c1, c2, THREE.MathUtils.clamp((pa.getY(i) + 1.15) / 2.3, 0, 1)); col.set([tmp.r, tmp.g, tmp.b], i * 3); }
    edges.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    mesh.add(new THREE.LineSegments(edges, lineMat));
    const grid = makeContours(geo, [0, 1], 0.17, gridMat, 0.004, -1.15, 1.15);
    grid.update(geo.attributes.position.array, geo.attributes.normal.array); mesh.add(grid.lines);
    group.add(mesh);
  }
  group.userData = { body, lineMat, gridMat };
  return group;
}

/* ---------- Material técnico da mão: corpo escuro + brilho nas bordas + linhas de varredura ---------- */
const handUniforms = { uTime: { value: 0 } };
/* Paleta por tema: corpo escuro + arestas luminosas azul -> ciano, a mesma linguagem do Coliseu */
const PALETTE = {
  light: { hand: 0x0f172a, sym: 0x0f172a, glow: 0x60a5fa, e1: 0x1669b6, e2: 0xbfdbfe, fx: 0x1669b6, scan: 0x84cc16, add: false },
  dark: { hand: 0x0b1426, sym: 0x0b1426, glow: 0x3b82f6, e1: 0x2563eb, e2: 0xe2e8f0, fx: 0x60a5fa, scan: 0xa3e635, add: true },
};
const glowU = { value: new THREE.Color(0x3b82f6) };
const themeNow = () => (document.documentElement.dataset.theme === "dark" ? PALETTE.dark : PALETTE.light);

/* corpo escuro metálico + brilho de borda (fresnel) + varredura; uCut esconde a malha além de um plano (efeito de scanner) */
function techMaterial(color = 0x0b1426, cut = { value: -100 }) {
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.35, side: THREE.DoubleSide, envMapIntensity: 1.0 });
  mat.polygonOffset = true; mat.polygonOffsetFactor = 1; mat.polygonOffsetUnits = 1;   // linhas por cima do volume
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uTime = handUniforms.uTime; sh.uniforms.uGlow = glowU; sh.uniforms.uCut = cut;
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vWPos;\nvarying vec3 vLPos;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvLPos = transformed;");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vWPos;\nvarying vec3 vLPos;\nuniform float uTime;\nuniform vec3 uGlow;\nuniform float uCut;")
      .replace("#include <opaque_fragment>", `
        if (vLPos.z < uCut) discard;
        float dca_f = pow(1.0 - saturate(dot(normalize(normal), normalize(vViewPosition))), 2.4);
        float dca_l = smoothstep(0.9, 1.0, abs(sin(vWPos.y * 10.0 - uTime * 0.7)));
        outgoingLight += uGlow * (dca_f * 0.5 + dca_l * 0.05);
        outgoingLight += vec3(0.75, 1.0, 0.45) * (1.0 - smoothstep(0.0, 0.1, vLPos.z - uCut)) * 1.8;
        #include <opaque_fragment>`);
  };
  mat.customProgramCacheKey = () => "dca-tech3";
  return mat;
}

function recolorSymbol(group, pal) {
  const c1 = new THREE.Color(pal.e1), c2 = new THREE.Color(pal.e2), tmp = new THREE.Color();
  group.traverse((o) => {
    if (!o.isLineSegments) return;
    const pa = o.geometry.getAttribute("position"), ca = o.geometry.getAttribute("color");
    for (let i = 0; i < pa.count; i++) { tmp.lerpColors(c1, c2, THREE.MathUtils.clamp((pa.getY(i) + 1.15) / 2.3, 0, 1)); ca.setXYZ(i, tmp.r, tmp.g, tmp.b); }
    ca.needsUpdate = true;
  });
}

/* Contornos: corta a malha por planos regulares e vira linhas luminosas (curvas de nível), como as fiadas do Coliseu.
   Cada ponto da linha fica preso a uma aresta da malha, então acompanha a deformação dos dedos. */
function makeContours(geo, axes, step, mat, off, y0, y1) {
  const P = geo.attributes.position.array, I = geo.index ? geo.index.array : Uint32Array.from({ length: P.length / 3 }, (_, i) => i);
  geo.computeBoundingBox();
  const bb = geo.boundingBox, S = [], P0 = Float32Array.from(P);
  axes.forEach((ax) => {
    const lo = bb.min.getComponent(ax);
    for (let t = 0; t < I.length; t += 3) {
      const v = [I[t], I[t + 1], I[t + 2]], f = v.map((i) => P[i * 3 + ax]), mn = Math.min(f[0], f[1], f[2]), mx = Math.max(f[0], f[1], f[2]);
      for (let k = Math.ceil((mn - lo) / step - 0.37); lo + (k + 0.37) * step <= mx; k++) {
        const pl = lo + (k + 0.37) * step, h = [];
        for (let e = 0; e < 3; e++) { const i = e, j = (e + 1) % 3; if ((f[i] - pl) * (f[j] - pl) < 0) h.push([v[i], v[j], (pl - f[i]) / (f[j] - f[i])]); }
        if (h.length === 2) S.push(h);
      }
    }
  });
  const n = S.length, A = new Uint32Array(2 * n), B = new Uint32Array(2 * n), T = new Float32Array(2 * n), pos = new Float32Array(n * 6), col = new Float32Array(n * 6);
  const fill = (order) => order.forEach((si, q) => { for (let e = 0; e < 2; e++) { const h = S[si][e]; A[2 * q + e] = h[0]; B[2 * q + e] = h[1]; T[2 * q + e] = h[2]; } });
  fill(S.map((_, i) => i));
  const lg = new THREE.BufferGeometry(), pa = new THREE.BufferAttribute(pos, 3), ca = new THREE.BufferAttribute(col, 3);
  lg.setAttribute("position", pa); lg.setAttribute("color", ca);
  const lines = new THREE.LineSegments(lg, mat); lines.frustumCulled = false;
  let pal = PALETTE.dark, zs = new Float32Array(n);
  const recolor = (p) => {
    pal = p; const c1 = new THREE.Color(p.e1), c2 = new THREE.Color(p.e2), tmp = new THREE.Color();
    for (let q = 0; q < 2 * n; q++) {
      const y = P0[A[q] * 3 + 1] * (1 - T[q]) + P0[B[q] * 3 + 1] * T[q];
      tmp.lerpColors(c1, c2, THREE.MathUtils.clamp((y - y0) / (y1 - y0), 0, 1)); col[q * 3] = tmp.r; col[q * 3 + 1] = tmp.g; col[q * 3 + 2] = tmp.b;
    }
    ca.needsUpdate = true;
  };
  const update = (Pd, Nd) => {
    for (let q = 0; q < 2 * n; q++) {
      const a = A[q] * 3, b = B[q] * 3, t = T[q], s = 1 - t;
      const nx = Nd[a] * s + Nd[b] * t, ny = Nd[a + 1] * s + Nd[b + 1] * t, nz = Nd[a + 2] * s + Nd[b + 2] * t, o = off / (Math.hypot(nx, ny, nz) || 1);
      pos[q * 3] = Pd[a] * s + Pd[b] * t + nx * o; pos[q * 3 + 1] = Pd[a + 1] * s + Pd[b + 1] * t + ny * o; pos[q * 3 + 2] = Pd[a + 2] * s + Pd[b + 2] * t + nz * o;
    }
    pa.needsUpdate = true;
  };
  /* ordena do pulso até a ponta dos dedos, para a linha "ser desenhada" na ordem da varredura */
  const sortByZ = (Pd, Nd) => {
    const zz = S.map((h) => Pd[h[0][0] * 3 + 2] * (1 - h[0][2]) + Pd[h[0][1] * 3 + 2] * h[0][2]), order = S.map((_, i) => i).sort((p, q) => zz[q] - zz[p]);
    fill(order); zs = Float32Array.from(order.map((i) => zz[i])); recolor(pal); update(Pd, Nd);
  };
  const reveal = (cut) => { let lo = 0, hi = n; while (lo < hi) { const m = (lo + hi) >> 1; if (zs[m] >= cut) lo = m + 1; else hi = m; } lg.setDrawRange(0, lo * 2); };
  recolor(pal);
  return { lines, update, recolor, sortByZ, reveal };
}

/* Posiciona o modelo: orientação, escala e PalmAnchor (centro da palma) na origem */
function fitHand(model, orient, root, wrist, rotDeg, scale) {
  orient.add(model);
  orient.rotation.set(0, 0, 0); orient.scale.setScalar(1); orient.position.set(0, 0, 0);
  wrist.position.set(0, 0, 0); wrist.rotation.x = 0; root.position.set(0, 0, 0); root.updateMatrixWorld(true);
  const size = new THREE.Box3().setFromObject(orient).getSize(new THREE.Vector3());   // medido sem rotação: o tamanho não muda ao girar
  orient.scale.setScalar((3.6 * scale) / Math.max(size.x, size.y, size.z));
  orient.rotation.set(...rotDeg.map((d) => THREE.MathUtils.degToRad(d)));
  orient.updateMatrixWorld(true);
  const anchor = model.getObjectByName("PalmAnchor");
  if (anchor) { const p = new THREE.Vector3(); anchor.getWorldPosition(p); orient.position.set(-p.x, -p.y, -p.z); }
  else { const box = new THREE.Box3().setFromObject(orient), c = box.getCenter(new THREE.Vector3()); orient.position.set(-c.x, -box.min.y, -c.z); }
}

/* ---------- Cena 1: mão (GLB) sustentando </> ----------
   Modelo: static/models/hand.glb ("jointed hands BJD", zacko, CC BY 4.0, simplificado).
   Valores data-* podem ser refinados na página /demo-mao/ (botão "Copiar valores"). */
function initHeroScene() {
  const el = document.getElementById("hero-scene");
  if (!el) return;
  const stage = createStage(el, { fov: 38, pos: new THREE.Vector3(0.6, 4.6, 9.2), look: new THREE.Vector3(0, 0.65, 0.7) });
  if (!stage) return;
  const { scene } = stage;

  const nums = (s, d) => (s ? s.split(",").map(Number) : d);
  const cfg = {
    rot: nums(el.dataset.handRotation, [0, 180, 0]), scale: parseFloat(el.dataset.handScale || "1.4"), off: nums(el.dataset.handOffset, [0, 0, 0]),
    sp: nums(el.dataset.symbolPos, [0, 1.85, 0]), ss: parseFloat(el.dataset.symbolScale || "0.7"),
  };

  const key = new THREE.DirectionalLight(0xe0ecff, 2.2); key.position.set(4, 7, 6); key.castShadow = true; scene.add(key);
  const rim = new THREE.DirectionalLight(0x00e5ff, 2.6); rim.position.set(-6, 3, -4); scene.add(rim);
  const fill = new THREE.PointLight(0x2563eb, 30, 14, 2); fill.position.set(0, -1, 4); scene.add(fill);

  const symbol = buildCodeSymbol(); symbol.scale.setScalar(cfg.ss); scene.add(symbol);
  const root = new THREE.Group(), wrist = new THREE.Group(), orient = new THREE.Group();
  root.add(wrist); wrist.add(orient); scene.add(root);
  const state = { lift: 0, lift2: 0, spin: 0, reveal: 1, rise: 1, fx: 0, scan: 1 };   // lift: mão; lift2: símbolo (um pouco atrasado = o impulso)

  const plain = new THREE.MeshStandardMaterial({ color: 0x14213d, metalness: 0.3, roughness: 0.45, side: THREE.DoubleSide });
  const handMeshes = [];
  stage.renderer.debug.onShaderError = () => handMeshes.forEach((m) => { m.material = plain; });   // se o shader falhar, usa material simples

  const handCut = { value: -100 }, handMat = techMaterial(PALETTE.light.hand, handCut);
  const handLineMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.7 });
  let lastCut = NaN, contours = null, scanRing = null;

  new GLTFLoader().load(
    el.dataset.handSrc,
    (gltf) => {
      const model = gltf.scene;
      fitHand(model, orient, root, wrist, cfg.rot, cfg.scale);
      root.position.set(...cfg.off);
      const tech = handMat;
      model.traverse((o) => { if (o.isMesh) { o.material = tech; o.castShadow = true; handMeshes.push(o); o.frustumCulled = false;
        const geo = o.geometry;
        contours = makeContours(geo, [2, 0], 0.15, handLineMat, 0.005, -1.3, 0.5);
        contours.sortByZ(geo.attributes.position.array, geo.attributes.normal.array);   // ordem de varredura: do pulso aos dedos
        o.add(contours.lines);
        const pts = Array.from({ length: 96 }, (_, i) => { const a = (i / 96) * 6.2832; return new THREE.Vector3(-0.15 + 1.3 * Math.cos(a), -0.4 + Math.sin(a), 0); });
        scanRing = new THREE.Group();   // anel do "scanner" que constrói a mão do pulso até os dedos
        [0, 0.07].forEach((dz) => { const l = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: 0x7df9ff, transparent: true, opacity: dz ? 0.35 : 1 })); l.position.z = dz; scanRing.add(l); });
        scanRing.visible = false; o.add(scanRing);
      } });
      lastCut = NaN; applyTheme();
      el.classList.remove("is-loading");
      intro();
    },
    undefined,
    (err) => {
      console.warn("[DevCodeArena] static/models/hand.glb ausente ou inválido. Nenhuma mão será exibida.", err);
      el.classList.remove("is-loading");
      el.classList.add("is-fallback");
      intro();
    }
  );

  /* efeitos de materialização: ondas de pulso e partículas saindo da palma */
  const rings = [0, 1].map(() => {
    const m = new THREE.Mesh(new THREE.RingGeometry(0.94, 1, 96).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    m.position.y = 0.06; wrist.add(m); return m;
  });
  const NP = 140, pPos = new Float32Array(NP * 3), seeds = Array.from({ length: NP }, () => ({ a: Math.random() * 6.283, r: Math.sqrt(Math.random()) * 0.9, s: 0.6 + Math.random() }));
  const pGeo = new THREE.BufferGeometry(); pGeo.setAttribute("position", new THREE.BufferAttribute(pPos, 3));
  const sparks = new THREE.Points(pGeo, new THREE.PointsMaterial({ color: 0x7df9ff, size: 0.045, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
  sparks.frustumCulled = false; wrist.add(sparks);
  symbol.children.forEach((m) => { m.userData.x = m.position.x; });

  /* abertura: mão fecha -> abre (dedos em cascata), pulso na palma, </> se materializa e sobe */
  let tl, last = 0;
  const intro = () => {
    last = performance.now();
    if (reduceMotion || !window.gsap) { Object.assign(state, { reveal: 1, rise: 1, spin: 1, fx: 0, scan: 1 }); return; }
    tl && tl.kill();
    Object.assign(state, { scan: 0, reveal: 0, rise: 0, fx: 0, spin: 0 });
    tl = gsap.timeline()
      .to(state, { scan: 1, duration: 2.3, ease: "power1.inOut" }, 0.2)         // 1) scanner constrói a mão, do pulso aos dedos
      .to(state, { fx: 1, duration: 1.8, ease: "none" }, 2.2)                   // 2) pulso e partículas na palma
      .to(state, { reveal: 1, duration: 1.6, ease: "power2.inOut" }, 2.4)       // 3) </> se forma
      .to(state, { rise: 1, duration: 2.4, ease: "elastic.out(1, 0.5)" }, 2.4)
      .to(state, { spin: 1, duration: 3, ease: "power2.out" }, 2.5);
  };
  if (!reduceMotion && window.gsap) {
    Object.assign(state, { scan: 0, reveal: 0, rise: 0 });   // começa com a mão fechada e sem símbolo
    gsap.to(state, { lift: 1, duration: 3.4, ease: "sine.inOut", yoyo: true, repeat: -1, delay: 5 });                 // a mão sobe e desce
    gsap.to(state, { lift2: 1, duration: 3.4, ease: "sine.inOut", yoyo: true, repeat: -1, delay: 5.28 });             // o símbolo acompanha, com atraso
  }

  const applyTheme = () => {
    const p = themeNow();
    glowU.value.set(p.glow); handMat.color.set(p.hand); symbol.userData.body.color.set(p.sym); recolorSymbol(symbol, p);
    contours && contours.recolor(p); scanRing && scanRing.children.forEach((l) => l.material.color.set(p.scan));
    rings.forEach((m) => { m.material.color.set(p.fx); m.material.blending = p.add ? THREE.AdditiveBlending : THREE.NormalBlending; m.material.needsUpdate = true; });
    sparks.material.color.set(p.fx); sparks.material.blending = p.add ? THREE.AdditiveBlending : THREE.NormalBlending; sparks.material.needsUpdate = true;
  };
  applyTheme();
  new MutationObserver(applyTheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  stage.onFrame = (t) => {
    handUniforms.uTime.value = t;
    const cut = state.scan >= 1 ? -100 : 1.15 - state.scan * 3.9;
    if (cut !== lastCut) { lastCut = cut; handCut.value = cut; contours && contours.reveal(cut); if (scanRing) { scanRing.position.z = cut; scanRing.visible = state.scan > 0 && state.scan < 1; } }
    const rv = Math.min(1, state.reveal), ud = symbol.userData;
    symbol.visible = rv > 0.01; ud.lineMat.opacity = 0.95 * rv; ud.gridMat.opacity = 0.3 * rv; ud.body.opacity = THREE.MathUtils.clamp((rv - 0.25) / 0.75, 0, 1);
    wrist.position.y = state.lift * 0.35; wrist.rotation.x = state.lift * 0.04;   // mão sobe e desce
    const r = state.rise;
    symbol.position.set(cfg.sp[0], cfg.sp[1] + state.lift2 * 0.45 + Math.sin(t * 0.8) * 0.03 - (1 - r) * 1.1, cfg.sp[2]);
    symbol.scale.setScalar(cfg.ss * (0.4 + 0.6 * r));
    symbol.rotation.set(0.16 + Math.sin(t * 0.5) * 0.05, t * 0.42 * state.spin, -0.05);
    symbol.children.forEach((m, i) => { m.position.x = m.userData.x * (0.35 + 0.65 * r); m.rotation.y = (1 - Math.min(r, 1)) * (i - 1) * 1.4; });   // peças se encaixam
    const f = state.fx;
    rings.forEach((m, i) => { const q = THREE.MathUtils.clamp(f * 1.4 - i * 0.28, 0, 1); m.scale.setScalar(0.3 + q * 2.1); m.material.opacity = q > 0 ? (1 - q) * 0.9 : 0; });
    sparks.material.opacity = Math.sin(Math.PI * Math.min(f, 1)) * 0.9;
    for (let i = 0; i < NP; i++) { const p = seeds[i], rad = p.r * (1 - f * 0.5), an = p.a + f * 2; pPos[i * 3] = Math.cos(an) * rad; pPos[i * 3 + 1] = f * p.s * 2.4; pPos[i * 3 + 2] = Math.sin(an) * rad; }
    pGeo.attributes.position.needsUpdate = true;
  };
}

/* ---------- Cena 2: Coliseu futurista (volume escuro + arquitetura em linhas) ---------- */
function floorTexture() {
  const c = document.createElement("canvas"); c.width = c.height = 512;
  const x = c.getContext("2d");
  x.fillStyle = "#0b1426"; x.fillRect(0, 0, 512, 512);
  x.strokeStyle = "rgba(0,229,255,.28)"; x.lineWidth = 1;
  for (let i = 0; i <= 512; i += 32) { x.beginPath(); x.moveTo(i, 0); x.lineTo(i, 512); x.moveTo(0, i); x.lineTo(512, i); x.stroke(); }
  x.fillStyle = "#00e5ff"; x.font = "700 150px ui-monospace, Menlo, Consolas, monospace";
  x.textAlign = "center"; x.textBaseline = "middle"; x.fillText("</>", 256, 262);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  return tex;
}

function buildColosseum() {
  const g = new THREE.Group();
  const A = 7, B = 5.6, N = 44, TIER_H = 1.55, ATTIC_H = 1.15, WALL = 0.85, TOP = 3 * TIER_H + ATTIC_H;

  // pontos equidistantes por comprimento de arco ao longo da elipse
  const S = 1440, samples = [], cum = [0];
  for (let i = 0; i <= S; i++) { const a = (i / S) * Math.PI * 2; samples.push(new THREE.Vector2(A * Math.cos(a), B * Math.sin(a))); if (i) cum.push(cum[i - 1] + samples[i].distanceTo(samples[i - 1])); }
  const L = cum[S];
  const at = (d) => { d = ((d % L) + L) % L; let i = cum.findIndex((c) => c >= d); i = Math.max(i, 1); const f = (d - cum[i - 1]) / (cum[i] - cum[i - 1]); return samples[i - 1].clone().lerp(samples[i], f); };
  const bayW = L / N;

  const bayShape = (h, holeFn) => { const s = new THREE.Shape(); s.moveTo(-bayW / 2, 0); s.lineTo(bayW / 2, 0); s.lineTo(bayW / 2, h); s.lineTo(-bayW / 2, h); s.closePath(); s.holes.push(holeFn()); return s; };
  const archHole = (h) => () => { const hw = bayW * 0.3, sp = h * 0.62, p = new THREE.Path(); p.moveTo(-hw, 0.1); p.lineTo(-hw, sp); p.absarc(0, sp, hw, Math.PI, 0, true); p.lineTo(hw, 0.1); p.closePath(); return p; };
  const windowHole = (h) => () => { const hw = bayW * 0.12, p = new THREE.Path(); p.moveTo(-hw, h * 0.32); p.lineTo(hw, h * 0.32); p.lineTo(hw, h * 0.78); p.lineTo(-hw, h * 0.78); p.closePath(); return p; };
  const extrude = (shape) => { const geo = new THREE.ExtrudeGeometry(shape, { depth: WALL, bevelEnabled: false, curveSegments: 12 }); geo.translate(0, 0, -WALL); return geo; };
  const tierGeo = extrude(bayShape(TIER_H, archHole(TIER_H)));
  const attGeo = extrude(bayShape(ATTIC_H, windowHole(ATTIC_H)));

  const ringGeo = (rx, ry, ix, iy, depth, y) => {
    const s = new THREE.Shape(); s.absellipse(0, 0, rx, ry, 0, Math.PI * 2, false);
    if (ix) { const h = new THREE.Path(); h.absellipse(0, 0, ix, iy, 0, Math.PI * 2, true); s.holes.push(h); }
    const geo = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: false, curveSegments: 96 });
    geo.rotateX(-Math.PI / 2); geo.translate(0, y, 0); return geo;
  };
  const ellipseLine = (rx, ry, y, mat) => {
    const pts = []; for (let i = 0; i < 200; i++) { const a = (i / 200) * Math.PI * 2; pts.push(new THREE.Vector3(rx * Math.cos(a), y, ry * Math.sin(a))); }
    return new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), mat);
  };

  // todas as peças viram UMA geometria: um único mesh de volume + um único conjunto de arestas
  const parts = [ringGeo(A + 0.9, B + 0.9, null, null, 0.2, -0.2)];
  const M = new THREE.Matrix4(), q = new THREE.Quaternion(), eu = new THREE.Euler(), v = new THREE.Vector3(), one = new THREE.Vector3(1, 1, 1);
  for (let i = 0; i < N; i++) {
    const p = at((i + 0.5) * bayW), t = at((i + 1) * bayW).sub(at(i * bayW));
    const n = new THREE.Vector2(t.y, -t.x).normalize(); if (n.dot(p) < 0) n.negate();
    q.setFromEuler(eu.set(0, Math.atan2(n.x, n.y), 0));
    for (let k = 0; k < 4; k++) {
      const geo = (k === 3 ? attGeo : tierGeo).clone();
      geo.applyMatrix4(M.compose(v.set(p.x, k * TIER_H, p.y), q, one)); parts.push(geo);
    }
  }
  for (let k = 1; k <= 4; k++) parts.push(ringGeo(A + 0.22, B + 0.22, A - WALL - 0.1, B - WALL - 0.1, 0.1, (k === 4 ? TOP : k * TIER_H) - 0.05));   // cornijas
  for (let k = 0; k < 6; k++) { const rx = A - WALL - 0.05 - k * 0.55, ry = B - WALL - 0.05 - k * 0.45; parts.push(ringGeo(rx, ry, rx - 0.55, ry - 0.45, 4.4 - k * 0.65, 0)); }   // cavea
  const arenaRx = A - WALL - 0.05 - 6 * 0.55 + 0.55, arenaRy = B - WALL - 0.05 - 6 * 0.45 + 0.45;
  parts.push(ringGeo(arenaRx, arenaRy, null, null, 0.3, 0));
  const body = mergeGeometries(parts);

  const bodyMat = new THREE.MeshStandardMaterial({ color: 0x0b1426, roughness: 0.55, metalness: 0.5, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  const mesh = new THREE.Mesh(body, bodyMat); mesh.castShadow = mesh.receiveShadow = true; g.add(mesh);

  // arestas com degradê vertical: azul na base, ciano no topo
  const edges = new THREE.EdgesGeometry(body, 28), pa = edges.getAttribute("position");
  const col = new Float32Array(pa.count * 3), c1 = new THREE.Color(0x2563eb), c2 = new THREE.Color(0x00e5ff), tmp = new THREE.Color();
  for (let i = 0; i < pa.count; i++) { tmp.lerpColors(c1, c2, THREE.MathUtils.clamp(pa.getY(i) / TOP, 0, 1)); col.set([tmp.r, tmp.g, tmp.b], i * 3); }
  edges.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  g.add(new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.95 })));

  // piso da arena: grade + </>
  const floor = new THREE.Mesh(new THREE.CircleGeometry(1, 96).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: floorTexture() }));
  floor.scale.set(arenaRx, 1, arenaRy); floor.position.y = 0.33; g.add(floor);
  g.add(ellipseLine(arenaRx, arenaRy, 0.34, new THREE.LineBasicMaterial({ color: 0x00e5ff })));

  // anel de varredura que percorre o edifício (lê a altura dos níveis)
  const scanMat = new THREE.LineBasicMaterial({ color: 0x7df9ff, transparent: true, opacity: 0.9 });
  const scan = ellipseLine(A + 0.28, B + 0.28, 0, scanMat); g.add(scan);
  g.userData = { scan, scanMat, TOP };
  return g;
}

function initArenaScene() {
  const el = document.getElementById("arena-scene");
  if (!el) return;
  const stage = createStage(el, { fov: 30, pos: new THREE.Vector3(0, 10.5, 26), look: new THREE.Vector3(0, 2.4, 0), exposure: 1.0, environment: false });
  if (!stage) return;
  const { scene } = stage;

  const key = new THREE.DirectionalLight(0xbfdcff, 1.8);
  key.position.set(8, 14, 9);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x00e5ff, 2.4); rim.position.set(-9, 5, -8); scene.add(rim);

  const colosseum = buildColosseum();
  scene.add(colosseum);
  const { scan, scanMat, TOP } = colosseum.userData;
  colosseum.rotation.y = -0.5;
  el.classList.remove("is-loading");

  stage.onFrame = (t) => {
    pointer.x += (pointer.tx - pointer.x) * 0.04; pointer.y += (pointer.ty - pointer.y) * 0.04;
    colosseum.rotation.y = -0.5 + t * 0.08 + pointer.x * 0.35;
    stage.camera.position.y = 10.5 - pointer.y * 1.2;
    const f = (t * 0.22) % 1;
    scan.position.y = f * TOP; scanMat.opacity = Math.sin(f * Math.PI) * 0.9;
  };
}

/* Mantém o símbolo de fallback visível enquanto cada cena ainda está carregando.
   A arena inferior só é construída quando o usuário se aproxima dela. */
function bootSceneWhenVisible(id, init, rootMargin) {
  const el = document.getElementById(id);
  if (!el) return;

  if (reduceMotion) {
    el.classList.remove("is-loading");
    el.classList.add("is-fallback");
    return;
  }

  let started = false;
  let observer;
  const start = () => {
    if (started) return;
    started = true;
    if (observer) observer.disconnect();
    loadThreeModules()
      .then(init)
      .catch((error) => {
        console.warn("[DevCodeArena] A cena 3D não pôde ser iniciada.", error);
        el.classList.remove("is-loading");
        el.classList.add("is-fallback");
      });
  };

  if ("IntersectionObserver" in window) {
    observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) start();
    }, { rootMargin, threshold: 0.01 });
    observer.observe(el);
  } else {
    start();
  }
}

bootSceneWhenVisible("hero-scene", initHeroScene, "80px 0px");
bootSceneWhenVisible("arena-scene", initArenaScene, "320px 0px");
