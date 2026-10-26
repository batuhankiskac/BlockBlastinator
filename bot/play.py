"""Block Blast'i iPhone'da WebDriverAgent üzerinden otomatik oynar.

    python play.py                  # oyna
    python play.py --advise         # sadece oku ve planı göster, dokunma
    python play.py --wda http://192.168.1.20:8100
"""
import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

from solver import LINES, board_to_int, place, solve
from vision import board_geom, read_board, read_pieces
from wda import WDA

HERE = Path(__file__).parent
SLOT = ["soldaki", "ortadaki", "sağdaki"]


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_config(path, cfg):
    Path(path).write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_board(board, highlight=()):
    hl = set(highlight)
    for r in range(8):
        print("   " + " ".join("@" if r * 8 + c in hl else ("#" if board[r * 8 + c] else ".") for c in range(8)))


def shape_cells(shape, r, c):
    return [(r + dr) * 8 + c + dc for dr, dc in shape]


def save_debug(img, cfg, board, pieces, plan, path):
    im = Image.fromarray(img).convert("RGB")
    d = ImageDraw.Draw(im)
    h, w = img.shape[:2]
    for key in ("board", "tray"):
        f = cfg[key]
        d.rectangle([f["x0"] * w, f["y0"] * h, f["x1"] * w, f["y1"] * h], outline="yellow", width=4)
    g = board_geom(img, cfg)
    for i, v in enumerate(board):
        if v:
            x, y = g["x0"] + ((i & 7) + .5) * g["cw"], g["y0"] + ((i >> 3) + .5) * g["ch"]
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill="white")
    colors = ["#f59f00", "#15aabf", "#e64980"]
    for si, m in enumerate(plan["moves"] if plan else []):
        for i in shape_cells(pieces[m["piece"]]["shape"], m["r"], m["c"]):
            x0, y0 = g["x0"] + (i & 7) * g["cw"], g["y0"] + (i >> 3) * g["ch"]
            d.rectangle([x0 + 6, y0 + 6, x0 + g["cw"] - 6, y0 + g["ch"] - 6], outline=colors[si], width=8)
    for p in pieces:
        if p:
            x, y = p["center"]
            d.line([x - 20, y, x + 20, y], fill="red", width=4)
            d.line([x, y - 20, x, y + 20], fill="red", width=4)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def find_shift(before, after, shape, r, c):
    """Parça hedeften kaymış mı? Gözlenen tahtayı açıklayan (dr, dc) kaymasını bulur."""
    cands = sorted(((dr, dc) for dr in range(-4, 5) for dc in range(-4, 5)), key=lambda s: abs(s[0]) + abs(s[1]))
    for dr, dc in cands:
        res = place(before, shape, r + dr, c + dc)
        if res and res[0] == after:
            return dr, dc
    return None


def main():
    ap = argparse.ArgumentParser(description="Block Blast botu (WebDriverAgent)")
    ap.add_argument("--wda", default="http://127.0.0.1:8100", help="WebDriverAgent adresi")
    ap.add_argument("--config", default=str(HERE / "config.json"))
    ap.add_argument("--advise", action="store_true", help="dokunmadan sadece planı göster")
    ap.add_argument("--max-moves", type=int, default=0, help="bu kadar hamleden sonra dur (0 = sınırsız)")
    ap.add_argument("--drag-api", choices=["w3c", "wda"], default="w3c")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows konsolunda Türkçe karakterler için

    cfg = load_config(args.config)
    wda = WDA(args.wda, args.drag_api)
    wda.start_session()
    win_w, _ = wda.window_size()
    debug_png = HERE / "debug" / "son.png"

    moves_done = empty_reads = bounces = 0
    pending, pending_board, img = [], None, None  # planın kalan hamleleri ve beklenen tahta
    while True:
        if img is None:
            img = wda.screenshot()
        scale = img.shape[1] / win_w  # piksel / nokta (iPhone 17 Pro'da 3)
        board = read_board(img, cfg)
        pieces = read_pieces(img, cfg)

        if not any(pieces):
            empty_reads += 1
            if args.advise or empty_reads > 6:
                save_debug(img, cfg, board, pieces, None, debug_png)
                print(f"Parça bulunamadı, durdum. Okunan görüntü: {debug_png}")
                return
            time.sleep(.5)
            img = None
            continue
        empty_reads = 0

        # Tahta beklendiği gibiyse planın kalanıyla devam et, değilse yeniden çöz.
        if pending and board_to_int(board) == pending_board and all(pieces[m["piece"]] for m in pending):
            plan = {"moves": pending}
        else:
            plan = solve(board_to_int(board), [p["shape"] if p else None for p in pieces])
        save_debug(img, cfg, board, pieces, plan, debug_png)
        if not plan["moves"]:
            print("Hiçbir parça sığmıyor, oyun bitti.")
            print_board(board)
            return

        if args.advise:
            print("Okunan tahta:")
            print_board(board)
            for si, m in enumerate(plan["moves"]):
                cl = ", ".join(LINES[i][1] for i in m["cleared"]) or "temizleme yok"
                print(f"{si + 1}. {SLOT[m['piece']]} parça -> satır {m['r'] + 1}, sütun {m['c'] + 1} ({cl})")
            print(f"Kontrol görüntüsü: {debug_png}")
            return

        # Planın sadece ilk hamlesini yap, sonra ekrana yeniden bak.
        m = plan["moves"][0]
        p = pieces[m["piece"]]
        shape = p["shape"]
        g = board_geom(img, cfg)
        ph = max(r for r, _ in shape) + 1
        pw = max(c for _, c in shape) + 1
        tx = g["x0"] + (m["c"] + pw / 2) * g["cw"]
        ty = g["y0"] + (m["r"] + ph / 2) * g["ch"]
        ox, oy = cfg["drag_offset_pt"]
        before = board_to_int(board)
        print(f"Hamle {moves_done + 1}: {SLOT[m['piece']]} parça -> satır {m['r'] + 1}, sütun {m['c'] + 1}")
        print_board(board, shape_cells(shape, m["r"], m["c"]))
        wda.drag(p["center"][0] / scale, p["center"][1] / scale, tx / scale + ox, ty / scale + oy, cfg["drag_ms"])
        time.sleep(cfg["settle_ms"] / 1000)

        # Kontrol: parça gerçekten hedefe mi düştü?
        img = wda.screenshot()  # bir sonraki tur da bu görüntüyü kullanır
        after = board_to_int(read_board(img, cfg))
        expected = place(before, shape, m["r"], m["c"])[0]
        pending, pending_board = [], None
        if after == expected:
            bounces = 0
            pending, pending_board = plan["moves"][1:], expected
        elif after == before:
            # Parça tahtaya bırakılamadı, geri döndü. Parmak hedefe göre fazla yukarıda kalmış olabilir.
            bounces += 1
            if bounces > 4:
                print("Parça art arda yerleşmedi. config.json'daki drag_offset_pt değerini kontrol et.")
                return
            cfg["drag_offset_pt"] = [ox, oy + g["ch"] / scale]
            save_config(args.config, cfg)
            print(f"Parça yerleşmedi, kaydırma ayarlandı: {cfg['drag_offset_pt']}")
            continue
        else:
            shift = find_shift(before, after, shape, m["r"], m["c"])
            if shift and shift != (0, 0):
                dr, dc = shift
                cfg["drag_offset_pt"] = [round(ox - dc * g["cw"] / scale, 1), round(oy - dr * g["ch"] / scale, 1)]
                save_config(args.config, cfg)
                print(f"Parça {dr:+d} satır, {dc:+d} sütun kaymış düştü. Kaydırma düzeltildi: {cfg['drag_offset_pt']}")
            bounces = 0

        moves_done += 1
        if args.max_moves and moves_done >= args.max_moves:
            print(f"{moves_done} hamle yapıldı, durdum.")
            return


if __name__ == "__main__":
    main()
