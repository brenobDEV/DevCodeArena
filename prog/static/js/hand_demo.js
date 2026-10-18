/* DevCodeArena — hand_demo.js: teste ISOLADO da mão 3D + </>. Nenhuma mão é inventada: sem GLB, nada de mão aparece. */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const $ = (s) => document.querySelector(s);
const stageEl = $("#demo-scene"), canvas = stageEl.querySelector("canvas"), status = $("#demo-status");
const state = { rx: 0, ry: 180, rz: 0, scale: 1.4, hx: 0, hy: 0, hz: 0, sx: 0, sy: 1.85, sz: 0, ss: 0.7, wire: false, tech: true, animate: true };

let renderer;
try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true }); }
catch (e) { status.hidden = false; status.textContent = "WebGL indisponível neste navegador."; throw e; }
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;

const scene = new THREE.Scene();
const pm = new THREE.PMREMGenerator(renderer);
scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;
const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
camera.position.set(0.6, 4.6, 9.2);                      // três quartos: palma, dedos, polegar e volume
const LOOK = new THREE.Vector3(0, 0.65, 0.7);

const key = new THREE.DirectionalLight(0xe0ecff, 2.4); key.position.set(4, 7, 6); key.castShadow = true; scene.add(key);
const rim = new THREE.DirectionalLight(0x00e5ff, 2.4); rim.position.set(-6, 3, -4); scene.add(rim);
const fill = new THREE.PointLight(0x2563eb, 30, 14, 2); fill.position.set(0, -1, 4); scene.add(fill);

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

const symbol = buildCodeSymbol(); scene.add(symbol);

const root = new THREE.Group();     // só translação (posição da mão)
const wrist = new THREE.Group();    // recebe o impulso do pulso
const orient = new THREE.Group();   // orientação/escala do modelo
root.add(wrist); wrist.add(orient); scene.add(root);

const techMat = techMaterial();
const wireMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, wireframe: true, transparent: true, opacity: 0.18, depthWrite: false });
let meshes = [];

function layout() {
  const keep = { y: wrist.position.y, rx: wrist.rotation.x };
  if (meshes.length) fitHand(orient.children[0], orient, root, wrist, [state.rx, state.ry, state.rz], state.scale);
  root.position.set(state.hx, state.hy, state.hz);
  wrist.position.y = keep.y; wrist.rotation.x = keep.rx;
  symbol.scale.setScalar(state.ss);
  $("#demo-out").textContent =
    `data-hand-rotation="${state.rx},${state.ry},${state.rz}"
data-hand-scale="${state.scale}"
data-hand-offset="${state.hx},${state.hy},${state.hz}"
` +
    `data-symbol-pos="${state.sx},${state.sy},${state.sz}"
data-symbol-scale="${state.ss}"`;
}
function applyFlags() { meshes.forEach((m) => { m.material = state.tech ? techMat : m.userData.orig; m.userData.wire.visible = state.wire; }); }

function setModel(model) {
  orient.clear(); meshes = [];
  orient.add(model);   // fitHand (em layout) reposiciona e reanexa
  model.traverse((o) => { if (o.isMesh) meshes.push(o); });
  meshes.forEach((m) => {
    m.userData.orig = m.material; m.castShadow = true;
    const w = m.isSkinnedMesh ? new THREE.SkinnedMesh(m.geometry, wireMat) : new THREE.Mesh(m.geometry, wireMat);
    if (m.isSkinnedMesh) w.bind(m.skeleton, m.bindMatrix);
    m.add(w); m.userData.wire = w;
  });
  applyFlags(); layout();
}

const loader = new GLTFLoader();
function load(url, revoke) {
  status.hidden = false; status.textContent = "Carregando modelo…";
  loader.load(url, (gltf) => { setModel(gltf.scene); status.hidden = true; if (revoke) URL.revokeObjectURL(url); },
    undefined,
    () => { status.hidden = false; status.textContent = "Nenhuma mão carregada. Coloque um GLB em static/models/hand.glb ou use \"Testar outro GLB\"."; });
}
load(stageEl.dataset.handSrc, false);
$("#demo-file").addEventListener("change", (e) => { const f = e.target.files[0]; if (f) load(URL.createObjectURL(f), true); });

document.querySelectorAll("[data-key]").forEach((inp) => {
  const key = inp.dataset.key, out = inp.parentElement.querySelector("output");
  const read = () => { state[key] = inp.type === "checkbox" ? inp.checked : parseFloat(inp.value); if (out) out.textContent = inp.value; if (inp.type === "checkbox") applyFlags(); layout(); };
  inp.addEventListener("input", read); read();
});
$("#demo-copy").addEventListener("click", () => { navigator.clipboard?.writeText($("#demo-out").textContent); $("#demo-copy").textContent = "Copiado"; setTimeout(() => ($("#demo-copy").textContent = "Copiar valores"), 1500); });

function resize() {
  const w = stageEl.clientWidth, h = stageEl.clientHeight; if (!w || !h) return;
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setSize(w, h, false);
  camera.aspect = w / h; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stageEl); resize();

const clock = new THREE.Clock(); let angle = 0;
renderer.debug.onShaderError = () => meshes.forEach((m) => { m.material = m.userData.orig; });
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
  handUniforms.uTime.value = t;
  const lift = state.animate ? Math.sin(t * 0.9) * 0.5 + 0.5 : 0;
  const lift2 = state.animate ? Math.sin(t * 0.9 - 0.6) * 0.5 + 0.5 : 0;
  const ramp = state.animate ? Math.min(t / 3, 1) : 0;
  angle += dt * 0.42 * ramp * ramp * (3 - 2 * ramp);
  wrist.position.y = lift * 0.35; wrist.rotation.x = lift * 0.04;              // impulso do pulso
  symbol.position.set(state.sx, state.sy + lift2 * 0.45 + Math.sin(t * 0.8) * 0.03 * ramp, state.sz);
  symbol.rotation.set(0.16 + Math.sin(t * 0.5) * 0.05 * ramp, angle, -0.05);   // gira sobre o próprio eixo
  camera.lookAt(LOOK); renderer.render(scene, camera);
});