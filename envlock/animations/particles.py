"""Animation « réseau de particules » : points mobiles reliés par des traits."""
from __future__ import annotations

import math
import random

from PySide6.QtGui import QColor, QPainter, QPen

from .base import BaseAnimation


class ParticlesAnimation(BaseAnimation):
    key = "particles"
    label = "Réseau de particules"

    def seed(self) -> None:
        count = int(self.options.get("count", 90))
        # Ajuste le nombre de points à la surface (aperçu = moins de points).
        area_factor = max(0.15, (self.width() * self.height()) / (1920 * 1080))
        count = max(12, int(count * min(1.0, area_factor)))
        w, h = self.width(), self.height()
        self.points = []
        for _ in range(count):
            self.points.append(
                [
                    random.uniform(0, w),
                    random.uniform(0, h),
                    random.uniform(-0.6, 0.6),
                    random.uniform(-0.6, 0.6),
                ]
            )

    def advance(self) -> None:
        w, h = self.width(), self.height()
        for p in self.points:
            p[0] += p[2]
            p[1] += p[3]
            if p[0] < 0 or p[0] > w:
                p[2] *= -1
            if p[1] < 0 or p[1] > h:
                p[3] *= -1

    def render_frame(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), self.bg_color("#0a0e17"))
        base = QColor(self.options.get("color", "#4f9dff"))
        link_dist = float(self.options.get("link_distance", 140))
        # Adapte la distance de liaison à la taille de l'aperçu.
        scale = min(1.0, max(self.width(), self.height()) / 1400)
        link_dist *= max(0.45, scale)

        # Traits entre points proches.
        for i, a in enumerate(self.points):
            for b in self.points[i + 1:]:
                dx = a[0] - b[0]
                dy = a[1] - b[1]
                dist = math.hypot(dx, dy)
                if dist < link_dist:
                    alpha = int(160 * (1 - dist / link_dist))
                    pen = QPen(QColor(base.red(), base.green(), base.blue(), alpha))
                    pen.setWidthF(1.0)
                    painter.setPen(pen)
                    painter.drawLine(int(a[0]), int(a[1]), int(b[0]), int(b[1]))

        # Points.
        painter.setPen(QColor(base.red(), base.green(), base.blue(), 230))
        painter.setBrush(QColor(base.red(), base.green(), base.blue(), 230))
        for p in self.points:
            painter.drawEllipse(int(p[0]) - 2, int(p[1]) - 2, 4, 4)
