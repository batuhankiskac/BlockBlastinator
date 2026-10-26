"""Ekran görüntüsünden tahtayı ve alttaki üç parçayı okur (index.html'deki algoritmanın aynısı)."""
import numpy as np


def _avg(img, x, y, r):
    h, w = img.shape[:2]
    x0, x1 = max(0, round(x - r)), min(w, round(x + r) + 1)
    y0, y1 = max(0, round(y - r)), min(h, round(y + r) + 1)
    return img[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)


def _dist(a, b):
    return float(np.linalg.norm(np.asarray(a, dtype=np.float32) - np.asarray(b, dtype=np.float32)))


def board_geom(img, cfg):
    h, w = img.shape[:2]
    b = cfg["board"]
    return {"x0": b["x0"] * w, "y0": b["y0"] * h, "cw": (b["x1"] - b["x0"]) * w / 8, "ch": (b["y1"] - b["y0"]) * h / 8}


def cell_center(geom, r, c):
    return geom["x0"] + (c + .5) * geom["cw"], geom["y0"] + (r + .5) * geom["ch"]


def read_board(img, cfg):
    g = board_geom(img, cfg)
    rad = min(g["cw"], g["ch"]) * .18
    cols = [_avg(img, *cell_center(g, i >> 3, i & 7), rad) for i in range(64)]
    # Boş hücreler koyu ve birbirine benzer: en koyu hücre "boş" referansı olur.
    lum = [c[0] * .3 + c[1] * .59 + c[2] * .11 for c in cols]
    ref = cols[int(np.argmin(lum))]
    return [1 if _dist(c, ref) > cfg["thr"] else 0 for c in cols]


def _normalize(cells):
    mr = min(r for r, _ in cells)
    mc = min(c for _, c in cells)
    return [(r - mr, c - mc) for r, c in cells]


def _detect_piece(img, x, y, w, h, pc, thr):
    k = max(2, round(min(w, h) * .04))
    corners = [_avg(img, x + k, y + k, k), _avg(img, x + w - k, y + k, k),
               _avg(img, x + k, y + h - k, k), _avg(img, x + w - k, y + h - k, k)]
    bg = np.mean(corners, axis=0)
    st = max(1, round(pc / 10))
    x0, y0 = round(x), round(y)
    region = img[y0:round(y + h):st, x0:round(x + w):st].astype(np.float32)
    mask = np.linalg.norm(region - bg, axis=2) > thr
    ys, xs = np.nonzero(mask)
    if len(xs) * st * st < pc * pc * .5:
        return None
    minx, maxx = x0 + xs.min() * st, x0 + xs.max() * st
    miny, maxy = y0 + ys.min() * st, y0 + ys.max() * st
    bw, bh = maxx - minx + st, maxy - miny + st
    nc = min(5, max(1, round(bw / pc)))
    nr = min(5, max(1, round(bh / pc)))
    cw, chh = bw / nc, bh / nr
    cells = [(r, c) for r in range(nr) for c in range(nc)
             if _dist(_avg(img, minx + (c + .5) * cw, miny + (r + .5) * chh, min(cw, chh) * .2), bg) > thr]
    if not cells:
        return None
    return {"shape": _normalize(cells), "center": (minx + bw / 2, miny + bh / 2)}


def read_pieces(img, cfg):
    h, w = img.shape[:2]
    g = board_geom(img, cfg)
    t = cfg["tray"]
    sw, th = (t["x1"] - t["x0"]) * w / 3, (t["y1"] - t["y0"]) * h
    pc = min(g["cw"], g["ch"]) * cfg["ratio"]
    return [_detect_piece(img, t["x0"] * w + s * sw, t["y0"] * h, sw, th, pc, cfg["thr"]) for s in range(3)]
