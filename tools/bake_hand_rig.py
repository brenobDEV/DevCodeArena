#!/usr/bin/env python3
"""
Gera prog/static/models/hand_rig.bin a partir de prog/static/models/hand.glb.

O hand.glb é uma malha única, sem ossos. Para mexer os dedos em tempo de execução, este
script descobre, para cada vértice, a qual dedo ele pertence e a que distância (medida sobre
a superfície) ele está da ponta desse dedo. O home.js usa esses dois números para dobrar
cada dedo em 3 articulações (MCP, PIP, DIP) sem precisar de esqueleto.

Dependências (só para rodar este script, não para o site): numpy e scipy.
    python tools/bake_hand_rig.py
    python tools/bake_hand_rig.py caminho/do/hand.glb saida/hand_rig.bin

Formato do .bin (little-endian):
    4 bytes  "HRG1"
    uint32   número de vértices N (precisa ser igual ao do GLB, senão o rig é ignorado)
    uint8[N] dono: 0 = palma/pulso, 1..5 = mindinho, anelar, médio, indicador, polegar
    uint8[N] distância geodésica até a ponta do dono, multiplicada por 60 (limitada a 255)

Se trocar o modelo da mão, as pontas dos dedos (TIP_REGIONS) e as articulações (em
hand_rig.js) precisam ser revistas.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parent.parent
GLB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "prog/static/models/hand.glb"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "prog/static/models/hand_rig.bin"

NAMES = ["pinky", "ring", "middle", "index", "thumb"]
# MCP (nó do dedo) em distância geodésica a partir da ponta; deve bater com hand_rig.js
MCP = {"pinky": 1.50, "ring": 1.85, "middle": 1.85, "index": 1.85, "thumb": 2.00}
MARGIN = 0.30   # quanto além do MCP o dedo ainda influencia a palma (mistura suave)
SCALE = 60.0


def read_glb(path):
    data = path.read_bytes()
    off, chunks = 12, {}
    while off < len(data):
        length, kind = struct.unpack("<II", data[off:off + 8])
        chunks[kind] = data[off + 8:off + 8 + length]
        off += 8 + length
    meta, blob = json.loads(chunks[0x4E4F534A]), chunks[0x004E4942]
    prim = meta["meshes"][0]["primitives"][0]

    def accessor(i, dtype, width):
        a = meta["accessors"][i]
        bv = meta["bufferViews"][a["bufferView"]]
        start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        return np.frombuffer(blob, dtype=dtype, count=a["count"] * width, offset=start).reshape(-1, width)

    pos = accessor(prim["attributes"]["POSITION"], np.float32, 3).astype(np.float64)
    idx_acc = meta["accessors"][prim["indices"]]
    idx_dtype = {5123: np.uint16, 5125: np.uint32}[idx_acc["componentType"]]
    tri = accessor(prim["indices"], idx_dtype, 1).reshape(-1, 3).astype(np.int64)
    return pos, tri


def main():
    P, tri = read_glb(GLB)
    n = len(P)
    edges = np.unique(np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1), axis=0)
    w = np.linalg.norm(P[edges[:, 0]] - P[edges[:, 1]], axis=1)
    graph = coo_matrix((np.r_[w, w], (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])), shape=(n, n)).tocsr()

    # pontas: o vértice mais distante do pulso dentro de cada região (modelo em repouso: dedos para -Z)
    wrist = np.where(P[:, 2] > 1.0)[0]
    from_wrist = dijkstra(graph, indices=wrist, min_only=True)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    regions = {
        "pinky": (x < -0.8) & (z < -0.5),
        "ring": (x > -0.85) & (x < -0.3) & (z < -1.0),
        "middle": (x > -0.3) & (x < 0.4) & (z < -1.0),
        "index": (x > 0.4) & (z < -1.0) & (y < 0.0),
        "thumb": (x > 0.15) & (y > 0.0),
    }
    dist = []
    for name in NAMES:
        cand = np.where(regions[name])[0]
        tip = cand[np.argmax(from_wrist[cand])]
        dist.append(dijkstra(graph, indices=tip))
        print(f"{name:7s} ponta no vértice {tip} em {np.round(P[tip], 3)}")
    dist = np.array(dist)                       # (5, n)

    slack = dist - np.array([MCP[k] for k in NAMES])[:, None]
    owner_idx = np.argmin(slack, axis=0)        # dedo cujo nó está mais perto
    near = slack[owner_idx, np.arange(n)] <= MARGIN
    owner = np.where(near, owner_idx + 1, 0).astype(np.uint8)
    d = dist[owner_idx, np.arange(n)]
    dq = np.clip(np.round(d * SCALE), 0, 255).astype(np.uint8)
    dq[owner == 0] = 255

    OUT.write_bytes(b"HRG1" + struct.pack("<I", n) + owner.tobytes() + dq.tobytes())
    print(f"{OUT} gravado: {OUT.stat().st_size} bytes, {n} vértices")
    for i, name in enumerate(NAMES, 1):
        print(f"  {name:7s}: {(owner == i).sum()} vértices")
    print(f"  palma  : {(owner == 0).sum()} vértices")


if __name__ == "__main__":
    main()
