/* DevCodeArena — hand_rig.js
   Dedos articulados para static/models/hand.glb.

   O GLB é uma malha única, sem ossos. tools/bake_hand_rig.py gera hand_rig.bin com, para cada
   vértice, o dedo a que ele pertence e a distância (sobre a superfície) até a ponta desse dedo.
   Aqui essa distância vira 3 articulações por dedo (DIP, PIP, MCP). Cada vértice gira em torno de
   cada articulação por uma fração do ângulo, então a pele dobra de forma contínua, sem rasgos.

   Módulo sem dependências: recebe arrays tipados e devolve funções. Pode ser testado no Node. */

const SCALE = 60;                // mesmo fator do bake: distância = byte / 60
const STEPS = 128;               // níveis da tabela de seno/cosseno (evita trigonometria por vértice)

/* Distância até a ponta de cada articulação, na ordem [DIP, PIP, MCP]. O MCP precisa bater com
   MCP em tools/bake_hand_rig.py. Ordem dos dedos = ids 1..5 do arquivo. */
export const FINGERS = [
  { name: "pinky", joints: [0.72, 1.15, 1.5] },
  { name: "ring", joints: [0.85, 1.38, 1.85] },
  { name: "middle", joints: [0.85, 1.38, 1.85] },
  { name: "index", joints: [0.85, 1.38, 1.85] },
  { name: "thumb", joints: [0.85, 1.4, 2.0] },
];
const HALF = [0.2, 0.2, 0.3];    // meia-largura da zona de dobra em cada articulação

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

/* position/normal: BufferAttribute do three (ou qualquer objeto com .array e .count).
   buffer: ArrayBuffer de hand_rig.bin. Devolve null se o arquivo não bater com a malha. */
export function createHandRig(position, normal, buffer) {
  if (!buffer || buffer.byteLength < 8) return null;
  const head = new DataView(buffer);
  const magic = String.fromCharCode(head.getUint8(0), head.getUint8(1), head.getUint8(2), head.getUint8(3));
  const n = head.getUint32(4, true);
  if (magic !== "HRG1" || n !== position.count || buffer.byteLength < 8 + 2 * n) return null;

  const owner = new Uint8Array(buffer, 8, n);
  const dist = new Uint8Array(buffer, 8 + n, n);
  const P = position.array, N = normal.array;
  const restP = Float32Array.from(P), restN = Float32Array.from(N);

  const fingers = FINGERS.map((def, k) => {
    const id = k + 1;
    let count = 0;
    for (let i = 0; i < n; i++) if (owner[i] === id) count++;
    if (!count) return null;

    const idx = new Uint32Array(count);
    const level = new Uint8Array(count * 3);          // fração (0..STEPS-1) de cada articulação por vértice
    const sum = def.joints.map(() => ({ y: 0, z: 0, c: 0 }));
    for (let i = 0, q = 0; i < n; i++) {
      if (owner[i] !== id) continue;
      const d = dist[i] / SCALE;
      idx[q] = i;
      for (let j = 0; j < 3; j++) {
        // 1 do lado da ponta da articulação, 0 do lado da palma, com transição suave
        level[q * 3 + j] = Math.round((1 - smooth(def.joints[j] - HALF[j], def.joints[j] + HALF[j], d)) * (STEPS - 1));
        if (Math.abs(d - def.joints[j]) < 0.05) { sum[j].y += restP[i * 3 + 1]; sum[j].z += restP[i * 3 + 2]; sum[j].c++; }
      }
      q++;
    }
    if (sum.some((s) => !s.c)) return null;            // articulação sem vértices: o rig não serve para este dedo
    const pivot = sum.map((s) => [s.y / s.c, s.z / s.c]);
    return { idx, level, pivot, angle: [0, 0, 0], applied: [0, 0, 0] };
  });

  const sinT = [new Float32Array(STEPS), new Float32Array(STEPS), new Float32Array(STEPS)];
  const cosT = [new Float32Array(STEPS), new Float32Array(STEPS), new Float32Array(STEPS)];

  /* flexão positiva = a ponta do dedo sobe para o lado da palma (+Y no modelo, que repousa com os dedos em -Z) */
  function pose(finger, dip, pip, mcp) {
    const f = fingers[finger];
    if (!f) return;
    f.angle[0] = dip; f.angle[1] = pip; f.angle[2] = mcp;
  }

  /* Aplica as poses na geometria. Devolve true se algum vértice mudou. */
  function apply() {
    let changed = false;
    for (const f of fingers) {
      if (!f) continue;
      const a = f.angle, p = f.applied;
      if (Math.abs(a[0] - p[0]) + Math.abs(a[1] - p[1]) + Math.abs(a[2] - p[2]) < 1e-5) continue;
      changed = true;
      p[0] = a[0]; p[1] = a[1]; p[2] = a[2];
      for (let j = 0; j < 3; j++) {
        for (let s = 0; s < STEPS; s++) { const t = (a[j] * s) / (STEPS - 1); sinT[j][s] = Math.sin(t); cosT[j][s] = Math.cos(t); }
      }
      const { idx, level, pivot } = f;
      for (let q = 0; q < idx.length; q++) {
        const o = idx[q] * 3;
        let y = restP[o + 1], z = restP[o + 2], ny = restN[o + 1], nz = restN[o + 2];
        // DIP primeiro, depois PIP, depois MCP: cada giro leva junto tudo que está mais perto da ponta
        for (let j = 0; j < 3; j++) {
          const lv = level[q * 3 + j];
          if (!lv) continue;
          const s = sinT[j][lv], c = cosT[j][lv], dy = y - pivot[j][0], dz = z - pivot[j][1];
          y = pivot[j][0] + dy * c - dz * s; z = pivot[j][1] + dy * s + dz * c;
          const ty = ny * c - nz * s; nz = ny * s + nz * c; ny = ty;
        }
        P[o + 1] = y; P[o + 2] = z; N[o + 1] = ny; N[o + 2] = nz;
      }
    }
    if (changed) { position.needsUpdate = true; normal.needsUpdate = true; }
    return changed;
  }

  return { owner, pose, apply, count: FINGERS.length, active: fingers.map(Boolean) };
}
