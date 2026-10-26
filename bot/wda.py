"""WebDriverAgent için küçük HTTP istemcisi: ekran görüntüsü ve sürükleme."""
import base64
import io

import numpy as np
import requests
from PIL import Image


class WDA:
    def __init__(self, url, drag_api="w3c"):
        self.url = url.rstrip("/")
        self.http = requests.Session()
        self.sid = None
        self.drag_api = drag_api

    def _req(self, method, path, body=None, timeout=30):
        r = self.http.request(method, self.url + path, json=body, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def start_session(self):
        data = self._req("POST", "/session", {"capabilities": {"alwaysMatch": {}}})
        self.sid = data.get("sessionId") or data["value"]["sessionId"]
        return self.sid

    def window_size(self):
        v = self._req("GET", f"/session/{self.sid}/window/size")["value"]
        return v["width"], v["height"]

    def screenshot(self):
        """RGB numpy dizisi döner (piksel cinsinden)."""
        png = base64.b64decode(self._req("GET", "/screenshot")["value"])
        return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))

    def drag(self, x1, y1, x2, y2, ms=350):
        """Koordinatlar nokta (point) cinsinden, piksel değil."""
        x1, y1, x2, y2 = (round(v) for v in (x1, y1, x2, y2))
        if self.drag_api == "wda":
            self._req("POST", f"/session/{self.sid}/wda/dragfromtoforduration",
                      {"fromX": x1, "fromY": y1, "toX": x2, "toY": y2, "duration": 0.15})
            return
        self._req("POST", f"/session/{self.sid}/actions", {"actions": [{
            "type": "pointer", "id": "finger1", "parameters": {"pointerType": "touch"},
            "actions": [
                {"type": "pointerMove", "duration": 0, "x": x1, "y": y1},
                {"type": "pointerDown", "button": 0},
                {"type": "pause", "duration": 120},
                {"type": "pointerMove", "duration": ms, "x": x2, "y": y2},
                {"type": "pause", "duration": 120},
                {"type": "pointerUp", "button": 0},
            ]}]})
