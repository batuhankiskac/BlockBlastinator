"""Block Blast çözücü. Tahta 64 bitlik bir tamsayı: hücre i = satır*8 + sütun."""

FULL = (1 << 64) - 1
ROW0 = 0xFF
ROW7 = 0xFF << 56
COL0 = sum(1 << (r * 8) for r in range(8))
COL7 = COL0 << 7

LINES = []
for r in range(8):
    LINES.append((sum(1 << (r * 8 + c) for c in range(8)), f"{r + 1}. satır"))
for c in range(8):
    LINES.append((sum(1 << (r * 8 + c) for r in range(8)), f"{c + 1}. sütun"))


def board_to_int(cells):
    return sum(1 << i for i, v in enumerate(cells) if v)


def int_to_board(b):
    return [(b >> i) & 1 for i in range(64)]


def placements(shape):
    """shape: [(satır, sütun), ...] sol üstü (0,0) olacak şekilde."""
    h = max(r for r, _ in shape) + 1
    w = max(c for _, c in shape) + 1
    out = []
    for r in range(9 - h):
        for c in range(9 - w):
            mask = 0
            for dr, dc in shape:
                mask |= 1 << ((r + dr) * 8 + c + dc)
            out.append((r, c, mask))
    return out


def rect(h, w):
    return [(r, c) for r in range(h) for c in range(w)]


# Gelecekte gelmesi muhtemel zor parçalar: hâlâ sığıyorlarsa tahta sağlıklıdır.
BIG = [(placements(rect(3, 3)), 12), (placements(rect(1, 5)), 6), (placements(rect(5, 1)), 6),
       (placements(rect(2, 3)), 3), (placements(rect(3, 2)), 3)]

_eval_cache = {}


def evaluate(b):
    hit = _eval_cache.get(b)
    if hit is not None:
        return hit
    # Komşu "dolu ya da duvar" maskeleri
    up = ((b << 8) | ROW0) & FULL
    down = (b >> 8) | ROW7
    left = (((b << 1) & FULL) & ~COL0) | COL0
    right = ((b >> 1) & ~COL7) | COL7
    empty = ~b & FULL
    filled = b.bit_count()
    holes = (empty & up & down & left & right).bit_count()
    trans = ((b ^ left) & FULL).bit_count() + (empty & COL7).bit_count() \
        + ((b ^ up) & FULL).bit_count() + (empty & ROW7).bit_count()
    fits = 0
    for pls, w in BIG:
        for _, _, m in pls:
            if not b & m:
                fits += w
                break
    s = -2 * filled - 8 * holes - trans + fits
    if len(_eval_cache) > 400_000:
        _eval_cache.clear()
    _eval_cache[b] = s
    return s


def clear_lines(b):
    cleared = [i for i, (m, _) in enumerate(LINES) if b & m == m]
    for i in cleared:
        b &= ~LINES[i][0]
    return b & FULL, cleared


def place(b, shape, r, c):
    """Parçayı (r, c)'ye koyar. Sığmıyorsa None döner."""
    mask = 0
    for dr, dc in shape:
        rr, cc = r + dr, c + dc
        if not (0 <= rr < 8 and 0 <= cc < 8):
            return None
        mask |= 1 << (rr * 8 + cc)
    if b & mask:
        return None
    return clear_lines(b | mask)


def solve(board, pieces):
    """board: 64 bitlik tamsayı, pieces: 3 elemanlı liste (şekil ya da None).
    En iyi sırayı döner: {"moves": [{"piece", "r", "c", "cleared"}], "unplaced", "score"}."""
    P = [placements(p) if p else None for p in pieces]
    rem0 = sum(1 << i for i, p in enumerate(P) if p)
    best = {"score": float("-inf"), "moves": [], "unplaced": 0}
    seen = set()
    path = []

    def rec(b, rem, acc):
        nonlocal best
        any_fit = False
        for i in range(3):
            if not rem & (1 << i):
                continue
            for r, c, m in P[i]:
                if b & m:
                    continue
                any_fit = True
                nb, cleared = clear_lines(b | m)
                n = len(cleared)
                gain = 20 * n + 10 * n * (n - 1) if n else 0
                nrem = rem & ~(1 << i)
                if nrem:
                    key = (nb, nrem, acc + gain)
                    if key in seen:
                        continue
                    seen.add(key)
                path.append({"piece": i, "r": r, "c": c, "cleared": cleared})
                rec(nb, nrem, acc + gain)
                path.pop()
        if not any_fit:
            unplaced = bin(rem).count("1")
            s = acc + evaluate(b) - 1000 * unplaced
            if s > best["score"]:
                best = {"score": s, "moves": list(path), "unplaced": unplaced}

    rec(board, rem0, 0)
    return best
