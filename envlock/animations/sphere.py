"""Animation « sphère de particules » (plexus sphere) qui tourne en 3D.

Des points répartis sur une sphère (répartition de Fibonacci) tournent lentement ;
les points proches sont reliés par des traits dont l'opacité dépend de la
profondeur, ce qui donne l'effet « globe réseau » lumineux.
"""
from __future__ import annotations

import math
import random

from PySide6.QtGui import QColor, QPainter, QPen

from .base import BaseAnimation


class SphereAnimation(BaseAnimation):
    key = "sphere"
    label = "Sphère de particules"

    def seed(self) -> None:
        count = int(self.options.get("count", 130))
        # Un peu moins de points sur un petit aperçu.
        if min(self.width(), self.height()) < 240:
            count = max(60, count // 2)

        self.pts: list[tuple[float, float, float]] = []
        # Répartition quasi-uniforme sur la sphère (spirale de Fibonacci).
        ga = math.pi * (3.0 - math.sqrt(5.0))  # angle d'or
        for i in range(count):
            y = 1 - (i / max(1, count - 1)) * 2  # de 1 à -1
            r = math.sqrt(max(0.0, 1 - y * y))
            theta = ga * i
            x = math.cos(theta) * r
            z = math.sin(theta) * r
            # Rayon légèrement variable + quelques points « satellites ».
            rad = random.uniform(0.9, 1.06)
            if random.random() < 0.12:
                rad = random.uniform(1.15, 1.45)
            self.pts.append((x * rad, y * rad, z * rad))

        # Adjacence figée : la rotation conserve les distances, on calcule donc
        # les arêtes une seule fois (points proches en 3D).
        link = float(self.options.get("link_distance", 0.46))
        self.edges: list[tuple[int, int, float]] = []
        n = len(self.pts)
        for i in range(n):
            ax, ay, az = self.pts[i]
            for j in range(i + 1, n):
                bx, by, bz = self.pts[j]
                d = math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)
                if d < link:
                    self.edges.append((i, j, 1.0 - d / link))

    def render_frame(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), self.bg_color("#05070d"))
        base = QColor(self.options.get("color", "#6fb3ff"))
        speed = float(self.options.get("speed", 0.006))

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) * 0.38

        yaw = self._frame * speed
        pitch = 0.42 + 0.10 * math.sin(self._frame * 0.004)
        cy_, sy_ = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        # Respiration douce.
        breathe = 1.0 + 0.03 * math.sin(self._frame * 0.02)

        # Projection de tous les points.
        proj = []
        for (x, y, z) in self.pts:
            # Rotation autour de Y (yaw).
            rx = x * cy_ + z * sy_
            rz = -x * sy_ + z * cy_
            # Rotation autour de X (pitch).
            ry = y * cp - rz * sp
            rz = y * sp + rz * cp
            depth = (rz + 1.4) / 2.8            # 0 = loin, 1 = proche
            depth = min(1.0, max(0.0, depth))
            persp = 1.0 / (1.0 - 0.32 * rz)
            sx = cx + rx * radius * persp * breathe
            sy = cy - ry * radius * persp * breathe
            proj.append((sx, sy, depth))

        # Traits (du plus lointain au plus proche).
        for (i, j, weight) in self.edges:
            xi, yi, di = proj[i]
            xj, yj, dj = proj[j]
            davg = (di + dj) / 2.0
            alpha = int(150 * weight * (0.25 + 0.75 * davg))
            if alpha <= 3:
                continue
            pen = QPen(QColor(base.red(), base.green(), base.blue(), alpha))
            pen.setWidthF(0.8 + davg)
            painter.setPen(pen)
            painter.drawLine(int(xi), int(yi), int(xj), int(yj))

        # Points par-dessus.
        painter.setPen(QColor(0, 0, 0, 0))
        for (sx, sy, depth) in proj:
            size = 1.2 + 2.6 * depth
            alpha = int(110 + 145 * depth)
            # Coeur clair pour les points proches.
            r = min(255, base.red() + int(60 * depth))
            g = min(255, base.green() + int(50 * depth))
            b = min(255, base.blue() + int(30 * depth))
            painter.setBrush(QColor(r, g, b, alpha))
            painter.drawEllipse(
                int(sx - size), int(sy - size), int(size * 2), int(size * 2)
            )
