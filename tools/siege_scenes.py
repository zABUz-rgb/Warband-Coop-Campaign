"""Native's Siege maps read from their scene files: where the battle server may put the garrison's bots.

A bot of the garrison must stand where the attackers can reach it and from where it can walk out. Native's
Siege puts its defenders at its spawn points, walkers at high points; some of those lie behind doors only a
player opens (a tower's room, the keep) or on a tower top, and a bot there never gets out (11-05 report).

This reads each map's entry points and AI mesh (the faces bots walk on), shuts its sally doors, gates,
movable ladders and siege towers, and leaves its room doors open (the battle server opens them when a siege
begins: castle_f_door_a/_b only a defender may open, and a bot never does). It keeps the entry points of the
mission (0..63) that lie on the part of the mesh holding the flag (entry 66), not above the top of the walls
and not next to a door. Where the attackers still walk to the flag with all of that shut (an earthen rampart),
it keeps those within NEAR_FLAG of the flag (Native's Siege keeps the attackers' spawns 70 m from it).

    python -I tools/siege_scenes.py [SceneObj folder]

prints DEFENDER_ENTRIES for src/coop/mp.py. The scene files are the game's (never in git).
"""
import collections
import heapq
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE_DIR = ROOT / "game" / "Modules" / "Native" / "SceneObj"
SIEGE_MAPS = [3, 10, 13, 16]  # src/coop/mp.py SIEGE_SCENES
FLAG, BASE = 66, 32           # header_common: multi_siege_flag_point, multi_initial_spawn_point_team_2
SHUT = ("sally", "portcullis", "earth_gate_a", "castle_gate", "dungeon_door", "door_h_", "house_roof_door")
DOORISH = ("door", "sally", "portcullis", "gate")
LEAF = 2.5          # m: a shut door is a wall this far to each side of its origin, along its x axis
GATE_LEAF = 1.8     # times that for a gate
NEAR_DOOR = 3.0     # m: faces this close to a shut door are taken out
SPAWN_OFF_DOOR = 3.5  # m: no spawn this close to any door
ABOVE_WALLS = 2.5   # m: no spawn higher than this above the ladders' tops (or the flag)
NEAR_FLAG = 60.0    # m: on a map open to the attackers, the garrison's spawns this close to the flag (the
                    # walled maps keep theirs within 59 m)


def read_scene(path):
  """(entry points {number: (x, y, z)}, props [(name, pos, rot, scale)], AI mesh (vertices, faces))."""
  data = Path(path).read_bytes()
  _, _, count = struct.unpack_from("<III", data, 0)
  off = 12
  entries, props = {}, []
  for _ in range(count):
    kind, = struct.unpack_from("<i", data, off)
    off += 12
    rot = struct.unpack_from("<9f", data, off)
    pos = struct.unpack_from("<3f", data, off + 36)
    n, = struct.unpack_from("<i", data, off + 48)
    off += 52
    name = data[off:off + n].decode("latin-1")
    off += n
    number, = struct.unpack_from("<i", data, off)
    scale = struct.unpack_from("<3f", data, off + 8)
    off += 20
    if kind == 1:
      entries[number] = pos
    elif kind == 0:
      props.append((name, pos, rot, scale))
  _, nv = struct.unpack_from("<II", data, off)
  off += 8
  verts = [struct.unpack_from("<3f", data, off + 12 * k) for k in range(nv)]
  off += 12 * nv
  ne, = struct.unpack_from("<i", data, off)
  off += 4 + 20 * ne
  nf, = struct.unpack_from("<i", data, off)
  off += 4
  faces = []
  for _ in range(nf):
    n, = struct.unpack_from("<i", data, off)
    vs = struct.unpack_from(f"<{n}i", data, off + 4)
    es = struct.unpack_from(f"<{n}i", data, off + 4 + 4 * n)
    off += 4 + 8 * n
    more, = struct.unpack_from("<i", data, off)
    off += 8 if more else 4
    faces.append((vs, es))
  return entries, props, (verts, faces)


def _inside(pt, poly):
  x, y = pt
  c = False
  for i in range(len(poly)):
    (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
    if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
      c = not c
  return c


def _crosses(a, b, c, d):
  def side(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) > 0
  return side(a, b, c) != side(a, b, d) and side(c, d, a) != side(c, d, b)


def _seg_dist(p, a, b):
  ax, ay = b[0] - a[0], b[1] - a[1]
  t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1)))
  return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def ladder_top(pos, rot, name):
  """A movable ladder stands raised where the scene has it: its top is its length up its z axis."""
  length = int(name.rsplit("_", 1)[1][:-1])
  return tuple(pos[k] + rot[6 + k] * length for k in range(3))


def defender_entries(path):
  entries, props, (verts, faces) = read_scene(path)
  cent = [tuple(sum(verts[v][k] for v in vs) / len(vs) for k in range(3)) for vs, _ in faces]
  walls, blocked, tops = [], set(), []
  for name, p, r, s in props:
    if any(w in name for w in SHUT) and "elevation" not in name:
      gate = "portcullis" in name or "gate" in name
      w = LEAF * s[0] * (GATE_LEAF if gate else 1)
      walls.append(((p[0] - r[0] * w, p[1] - r[1] * w), (p[0] + r[0] * w, p[1] + r[1] * w), p[2] - 1.5, p[2] + 3))
      reach = NEAR_DOOR * (1.6 if gate else 1)
      blocked |= {i for i, c in enumerate(cent) if math.hypot(c[0] - p[0], c[1] - p[1]) < reach and abs(c[2] - p[2]) < 4}
    if "ladder_move" in name:
      top = ladder_top(p, r, name)
      tops.append(top[2])
      blocked |= {i for i, c in enumerate(cent) if _seg_dist(c, p, top) < 2.5 and p[2] + 1 < c[2] < top[2] - 0.7}
    if name in ("spr_belfry_a", "spr_belfry_b"):
      y = r[3:6]
      foot, front = (p[0] - 10 * y[0], p[1] - 10 * y[1]), (p[0] + 6 * y[0], p[1] + 6 * y[1])
      blocked |= {i for i, c in enumerate(cent) if _seg_dist(c, foot, front) < 4 and c[2] > p[2] + 0.8}
  by_edge = collections.defaultdict(list)
  for i, (_, es) in enumerate(faces):
    if i not in blocked:
      for e in es:
        by_edge[e].append(i)
  adj = collections.defaultdict(set)
  for fs in by_edge.values():
    for a in fs:
      for b in fs:
        if a < b:
          mid = (cent[a][2] + cent[b][2]) / 2
          if not any(z0 <= mid <= z1 and _crosses(cent[a][:2], cent[b][:2], s0, s1) for s0, s1, z0, z1 in walls):
            adj[a].add(b)
            adj[b].add(a)

  def face_at(p):
    best = None
    for i, (vs, _) in enumerate(faces):
      if _inside(p[:2], [verts[v][:2] for v in vs]):
        gap = abs(cent[i][2] - p[2])
        if best is None or gap < best[1]:
          best = (i, gap)
    return best[0] if best else min(range(len(faces)), key=lambda i: math.dist(cent[i], p))

  def walk(src):
    dist, q = {src: 0.0}, [(0.0, src)]
    while q:
      d, u = heapq.heappop(q)
      if d <= dist[u]:
        for v in adj[u]:
          nd = d + math.dist(cent[u], cent[v])
          if nd < dist.get(v, 1e18):
            dist[v] = nd
            heapq.heappush(q, (nd, v))
    return dist

  where = {no: face_at(p) for no, p in entries.items()}
  from_flag = walk(where[FLAG])
  apart = where[BASE] not in from_flag
  flag = entries[FLAG]
  highest = max(tops + [entries[FLAG][2]]) + ABOVE_WALLS
  doors = [p for name, p, _, _ in props if any(w in name for w in DOORISH) and "elevation" not in name]
  keep = []
  for no in sorted(n for n in entries if n <= 63):
    f, p = where[no], entries[no]
    if f in blocked or f not in from_flag or p[2] > highest:
      continue
    if not apart and math.hypot(p[0] - flag[0], p[1] - flag[1]) > NEAR_FLAG:
      continue
    if any(math.dist(p, d) < SPAWN_OFF_DOOR for d in doors):
      continue
    keep.append(no)
  return keep


def all_maps(folder=SCENE_DIR):
  return {f"scn_multi_scene_{n}": defender_entries(Path(folder) / f"scn_multi_scene_{n}.sco") for n in SIEGE_MAPS}


if __name__ == "__main__":
  found = all_maps(sys.argv[1] if len(sys.argv) > 1 else SCENE_DIR)
  print("DEFENDER_ENTRIES = {")
  for scene, keep in found.items():
    print(f'  "{scene}": {keep},')
  print("}")
