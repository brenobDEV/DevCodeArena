/* DevCodeArena — home.js: cena da mão + </> e Coliseu 3D (Three.js + GSAP) */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
addEventListener("pointermove", (e) => {
  pointer.tx = (e.clientX / innerWidth) * 2 - 1;
  pointer.ty = (e.clientY / innerHeight) * 2 - 1;
}, { passive: true });

/* ---------- Palco genérico: renderer, câmera, resize, pausa fora da tela ---------- */
function createStage(el, { fov, pos, look, exposure = 1.05 }) {
  const canvas = el.querySelector("canvas");
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  } catch (err) { el.classList.add("is-fallback"); return null; }

  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = exposure;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envRT = pmrem.fromScene(new RoomEnvironment(), 0.04);
  scene.environment = envRT.texture;
  scene.environmentIntensity = 0.55;

  const camera = new THREE.PerspectiveCamera(fov, 1, 0.1, 100);
  camera.position.copy(pos);
  const clock = new THREE.Clock();
  const stage = { scene, camera, renderer, onFrame: () => {}, look: look.clone() };
  let raf = 0, visible = false;

  const draw = () => {
    stage.onFrame(clock.getElapsedTime(), Math.min(clock.getDelta(), 0.05));
    camera.lookAt(stage.look);
    renderer.render(scene, camera);
  };
  const loop = () => { draw(); raf = requestAnimationFrame(loop); };
  const sync = () => {
    cancelAnimationFrame(raf);
    if (reduceMotion) { draw(); return; }
    if (visible && !document.hidden) { clock.getDelta(); loop(); }
  };
  const resize = () => {
    const w = el.clientWidth, h = el.clientHeight;
    if (!w || !h) return;
    renderer.setPixelRatio(Math.min(devicePixelRatio, w < 520 ? 1.5 : 2));
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
    envRT.dispose(); pmrem.dispose(); renderer.dispose();
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
  const body = techMaterial(0x0b1426);
  body.polygonOffset = true; body.polygonOffsetFactor = 1; body.polygonOffsetUnits = 1;   // arestas por cima do volume
  const lineMat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.95 });
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
    group.add(mesh);
  }
  return group;
}

/* ---------- Material técnico da mão: corpo escuro + brilho nas bordas + linhas de varredura ---------- */
const handUniforms = { uTime: { value: 0 } };
function techMaterial(color = 0x0b1426) {
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.36, metalness: 0.65, side: THREE.DoubleSide, envMapIntensity: 1.1 });
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uTime = handUniforms.uTime;
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vWPos;")
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vWPos;\nuniform float uTime;")
      .replace("#include <opaque_fragment>", `
        float dca_f = pow(1.0 - saturate(dot(normalize(normal), normalize(vViewPosition))), 2.2);
        float dca_l = smoothstep(0.9, 1.0, abs(sin(vWPos.y * 10.0 - uTime * 0.7)));
        outgoingLight += vec3(0.0, 0.9, 1.0) * (dca_f * 0.85 + dca_l * 0.16);
        #include <opaque_fragment>`);
  };
  mat.customProgramCacheKey = () => "dca-tech";
  return mat;
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
  const stage = createStage(el, { fov: 34, pos: new THREE.Vector3(4.4, 5.0, 8.8), look: new THREE.Vector3(0.3, 0.75, 0.9) });
  if (!stage) return;
  const { scene } = stage;

  const nums = (s, d) => (s ? s.split(",").map(Number) : d);
  const cfg = {
    rot: nums(el.dataset.handRotation, [0, -140, 0]), scale: parseFloat(el.dataset.handScale || "1.1"), off: nums(el.dataset.handOffset, [0, 0, 0]),
    sp: nums(el.dataset.symbolPos, [0, 1.6, 0]), ss: parseFloat(el.dataset.symbolScale || "0.62"),
  };

  const key = new THREE.DirectionalLight(0xe0ecff, 2.2); key.position.set(4, 7, 6); key.castShadow = true; scene.add(key);
  const rim = new THREE.DirectionalLight(0x00e5ff, 2.6); rim.position.set(-6, 3, -4); scene.add(rim);
  const fill = new THREE.PointLight(0x2563eb, 30, 14, 2); fill.position.set(0, -1, 4); scene.add(fill);

  const symbol = buildCodeSymbol(); symbol.scale.setScalar(cfg.ss); scene.add(symbol);
  const root = new THREE.Group(), wrist = new THREE.Group(), orient = new THREE.Group();
  root.add(wrist); wrist.add(orient); scene.add(root);
  const state = { lift: 0, spin: 0 };

  const plain = new THREE.MeshStandardMaterial({ color: 0x14213d, metalness: 0.3, roughness: 0.45, side: THREE.DoubleSide });
  const handMeshes = [];
  stage.renderer.debug.onShaderError = () => handMeshes.forEach((m) => { m.material = plain; });   // se o shader falhar, usa material simples

  new GLTFLoader().load(
    el.dataset.handSrc,
    (gltf) => {
      const model = gltf.scene;
      fitHand(model, orient, root, wrist, cfg.rot, cfg.scale);
      root.position.set(...cfg.off);
      const tech = techMaterial();
      model.traverse((o) => { if (o.isMesh) { o.material = tech; o.castShadow = true; handMeshes.push(o); } });
    },
    undefined,
    (err) => console.warn("[DevCodeArena] static/models/hand.glb ausente ou inválido. Nenhuma mão será exibida.", err)
  );

  if (!reduceMotion && window.gsap) {
    gsap.to(state, { spin: 1, duration: 3.2, ease: "power2.out" });
    gsap.to(state, { lift: 1, duration: 3.4, ease: "sine.inOut", yoyo: true, repeat: -1 });
  } else { state.spin = 1; }

  stage.onFrame = (t) => {
    handUniforms.uTime.value = t;
    wrist.position.y = state.lift * 0.12; wrist.rotation.x = state.lift * 0.05;   // impulso do pulso
    symbol.position.set(cfg.sp[0], cfg.sp[1] + state.lift * 0.15 + Math.sin(t * 0.8) * 0.03, cfg.sp[2]);
    symbol.rotation.set(0.16 + Math.sin(t * 0.5) * 0.05, t * 0.42 * state.spin, -0.05);
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
  const stage = createStage(el, { fov: 30, pos: new THREE.Vector3(0, 10.5, 26), look: new THREE.Vector3(0, 2.4, 0), exposure: 1.0 });
  if (!stage) return;
  const { scene } = stage;

  const key = new THREE.DirectionalLight(0xbfdcff, 1.8);
  key.position.set(8, 14, 9); key.castShadow = true; key.shadow.mapSize.set(1024, 1024);
  Object.assign(key.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 40 }); key.shadow.bias = -0.0005;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x00e5ff, 2.4); rim.position.set(-9, 5, -8); scene.add(rim);

  const colosseum = buildColosseum();
  scene.add(colosseum);
  const { scan, scanMat, TOP } = colosseum.userData;
  colosseum.rotation.y = -0.5;

  stage.onFrame = (t) => {
    pointer.x += (pointer.tx - pointer.x) * 0.04; pointer.y += (pointer.ty - pointer.y) * 0.04;
    colosseum.rotation.y = -0.5 + t * 0.08 + pointer.x * 0.35;
    stage.camera.position.y = 10.5 - pointer.y * 1.2;
    const f = (t * 0.22) % 1;
    scan.position.y = f * TOP; scanMat.opacity = Math.sin(f * Math.PI) * 0.9;
  };
}

initHeroScene();
initArenaScene();
