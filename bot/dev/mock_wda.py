"""Telefonsuz test için sahte WebDriverAgent sunucusu.

Basit bir blok bulmacası çizer, sürüklemeleri işler. Gerçek oyundaki gibi
sürüklenen parça parmağın biraz yukarısında durur (LIFT_CELLS), böylece botun
kaydırma düzeltmesi de test edilir.

    python dev/mock_wda.py --port 8100
"""
import argparse
import base64
import io
import json
import random
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from solver import int_to_board, place  # noqa: E402

PT_W, PT_H, SCALE = 402, 874, 3  # iPhone 17 Pro: 402x874 nokta, 3x
W, H = PT_W * SCALE, PT_H * SCALE
BOARD = (0.05, 0.30, 0.95)  # x0, y0, x1 (kare tahta)
TRAY = (0.03, 0.74, 0.97, 0.88)
COLORS = [(232, 89, 12), (250, 176, 5), (64, 192, 87), (34, 139, 230), (190, 75, 219), (240, 62, 62)]
SHAPES = [
    [(0, 0)], [(0, 0), (0, 1)], [(0, 0), (1, 0)], [(0, 0), (0, 1), (0, 2)], [(0, 0), (1, 0), (2, 0)],
    [(0, 0), (0, 1), (0, 2), (0, 3)], [(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 0), (0, 1), (1, 0), (1, 1)],
    [(0, 0), (1, 0), (2, 0), (2, 1)], [(0, 1), (1, 1), (2, 0), (2, 1)], [(0, 0), (0, 1), (0, 2), (1, 1)],
    [(0, 0), (0, 1), (1, 1), (1, 2)], [(r, c) for r in range(3) for c in range(3)],
    [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], [(r, c) for r in range(2) for c in range(3)],
]


class Game:
    def __init__(self, lift_cells, seed):
        self.rng = random.Random(seed)
        self.board = 0
        self.lift = lift_cells
        self.score = 0
        self.refill()

    def refill(self):
        self.tray = [self.rng.choice(SHAPES) for _ in range(3)]

    def geom(self):
        bx = BOARD[0] * W
        by = BOARD[1] * H
        cs = (BOARD[2] - BOARD[0]) * W / 8
        return bx, by, cs

    def slot_rect(self, s):
        sw = (TRAY[2] - TRAY[0]) * W / 3
        return TRAY[0] * W + s * sw, TRAY[1] * H, sw, (TRAY[3] - TRAY[1]) * H

    def render(self):
        im = Image.new("RGB", (W, H), (62, 92, 172))
        d = ImageDraw.Draw(im)
        bx, by, cs = self.geom()
        d.rectangle([bx, by, bx + 8 * cs, by + 8 * cs], fill=(22, 30, 68))
        cells = int_to_board(self.board)
        for i, v in enumerate(cells):
            r, c = divmod(i, 8)
            col = COLORS[(r + c) % 6] if v else (28, 36, 78)
            d.rectangle([bx + c * cs + 2, by + r * cs + 2, bx + (c + 1) * cs - 3, by + (r + 1) * cs - 3], fill=col)
        ps = cs * .5
        for s, shape in enumerate(self.tray):
            if not shape:
                continue
            x, y, sw, sh = self.slot_rect(s)
            pw = (max(c for _, c in shape) + 1) * ps
            ph = (max(r for r, _ in shape) + 1) * ps
            ox, oy = x + (sw - pw) / 2, y + (sh - ph) / 2
            for r, c in shape:
                d.rectangle([ox + c * ps + 1, oy + r * ps + 1, ox + (c + 1) * ps - 2, oy + (r + 1) * ps - 2],
                            fill=COLORS[(s + 2) % 6])
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def drag(self, x1, y1, x2, y2):
        x1, y1, x2, y2 = (v * SCALE for v in (x1, y1, x2, y2))
        slot = next((s for s in range(3) if self.tray[s] and
                     self.slot_rect(s)[0] <= x1 < self.slot_rect(s)[0] + self.slot_rect(s)[2] and
                     self.slot_rect(s)[1] <= y1 < self.slot_rect(s)[1] + self.slot_rect(s)[3]), None)
        if slot is None:
            return "boş yere dokunuldu"
        shape = self.tray[slot]
        bx, by, cs = self.geom()
        ph = max(r for r, _ in shape) + 1
        pw = max(c for _, c in shape) + 1
        # Parça merkezi parmağın LIFT hücre yukarısında
        cx, cy = x2, y2 - self.lift * cs
        c = round((cx - bx) / cs - pw / 2)
        r = round((cy - by) / cs - ph / 2)
        res = place(self.board, shape, r, c)
        if not res:
            return f"geri döndü (satır {r + 1}, sütun {c + 1} geçersiz)"
        self.board, cleared = res
        self.score += len(shape) + 10 * len(cleared)
        self.tray[slot] = None
        if not any(self.tray):
            self.refill()
        return f"satır {r + 1}, sütun {c + 1}; {len(cleared)} çizgi; skor {self.score}"


def make_handler(game):
    class H(BaseHTTPRequestHandler):
        def _send(self, value, extra=None):
            body = {"value": value, "sessionId": "mock"}
            body.update(extra or {})
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.endswith("/window/size"):
                self._send({"width": PT_W, "height": PT_H})
            elif self.path == "/screenshot":
                self._send(game.render())
            else:
                self._send({"ready": True})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/session":
                self._send({"sessionId": "mock"})
            elif self.path.endswith("/actions"):
                moves = [a for a in body["actions"][0]["actions"] if a["type"] == "pointerMove"]
                msg = game.drag(moves[0]["x"], moves[0]["y"], moves[-1]["x"], moves[-1]["y"])
                print("sürükleme:", msg, flush=True)
                self._send(None)
            elif self.path.endswith("/wda/dragfromtoforduration"):
                print("sürükleme:", game.drag(body["fromX"], body["fromY"], body["toX"], body["toY"]), flush=True)
                self._send(None)
            else:
                self._send(None)

        def log_message(self, *a):
            pass

    return H


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--lift", type=float, default=2.0, help="parça parmağın kaç hücre yukarısında dursun")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Sahte WDA http://localhost:{a.port} adresinde", flush=True)
    HTTPServer(("127.0.0.1", a.port), make_handler(Game(a.lift, a.seed))).serve_forever()
