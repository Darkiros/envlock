"""Animation « dégradé fluide » : blobs colorés qui se déplacent en douceur."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPainter, QRadialGradient

from .base import BaseAnimation


class GradientAnimation(BaseAnimation):
    key = "gradient"
    label = "Dégradé fluide"

    def seed(self) -> None:
        colors = self.options.get("colors", ["#5b2be0", "#2b6be0", "#e02b8a"])
        self.blobs = []
        for i, c in enumerate(colors):
            self.blobs.append(
                {
                    "color": QColor(c),
                    "phase": i * 2.1,
                    "sx": 0.30 + 0.12 * i,   # vitesse x
                    "sy": 0.22 + 0.15 * i,   # vitesse y
                    "ox": 0.5 + 0.3 * math.cos(i),
                    "oy": 0.5 + 0.3 * math.sin(i),
                }
            )

    def render_frame(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), self.bg_color("#07070d"))
        w, h = self.width(), self.height()
        t = self._frame / 60.0
        radius = max(w, h) * 0.55
        painter.setPen(QColor(0, 0, 0, 0))
        for b in self.blobs:
            cx = (0.5 + 0.32 * math.sin(t * b["sx"] + b["phase"])) * w
            cy = (0.5 + 0.32 * math.cos(t * b["sy"] + b["phase"])) * h
            grad = QRadialGradient(QPointF(cx, cy), radius)
            col = b["color"]
            grad.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), 170))
            grad.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
            painter.setBrush(grad)
            painter.drawRect(self.rect())
