"""Animation « sphère de particules » (plexus sphere) qui tourne en 3D.

Des points répartis sur une sphère (répartition de Fibonacci) tournent lentement ;
les points proches sont reliés par des traits. Rendu en blending additif avec
dégradé de profondeur (bleu profond à l'arrière → cyan lumineux à l'avant) et
halos, pour l'effet « globe réseau » lumineux.
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
        count = int(self.options.get("count", 170))
        if min(self.width(), self.height()) < 240:  # aperçu = moins de points
            count = max(70, count // 2)

        self.pts: list[tuple[float, float, float]] = []
        ga = math.pi * (3.0 - math.sqrt(5.0))  # angle d'or
        for i in range(count):
            y = 1 - (i / max(1, count - 1)) * 2  # de 1 à -1
            r = math.sqrt(max(0.0, 1 - y * y))
            theta = ga * i
            x = math.cos(theta) * r
            z = math.sin(theta) * r
            # Rayon quasi constant + rares satellites proches (arcs externes).
            rad = random.uniform(0.94, 1.04)
            if random.random() < 0.08:
                rad = random.uniform(1.08, 1.22)
            self.pts.append((x * rad, y * rad, z * rad))

        # Adjacence figée : la rotation conserve les distances 3D.
        link = float(self.options.get("link_distance", 0.42))
        self.edges: list[tuple[int, int, float]] = []
        n = len(self.pts)
        for i in range(n):
            ax, ay, az = self.pts[i]
            for j in range(i + 1, n):
                bx, by, bz = self.pts[j]
                d = math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)
                if d < link:
                    self.edges.append((i, j, 1.0 - d / link))

    # -- couleurs de profondeur ----------------------------------------
    def _depth_color(self, base: QColor, depth: float, alpha: int) -> QColor:
        # Arrière : bleu sombre. Avant : cyan clair proche du blanc.
        r = int(30 + (base.red() + 90 - 30) * depth)
        g = int(70 + (base.green() + 60 - 70) * depth)
        b = int(120 + (min(255, base.blue() + 20) - 120) * depth)
        return QColor(min(255, r), min(255, g), min(255, b), alpha)

    def render_frame(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), self.bg_color("#04060c"))
        base = QColor(self.options.get("color", "#63d0ff"))
        speed = float(self.options.get("speed", 0.006))

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) * 0.38

        yaw = self._frame * speed
        pitch = 0.42 + 0.09 * math.sin(self._frame * 0.004)
        cyw, syw = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        breathe = 1.0 + 0.025 * math.sin(self._frame * 0.02)

        # Projection de tous les points.
        proj = []
        for (x, y, z) in self.pts:
            rx = x * cyw + z * syw
            rz = -x * syw + z * cyw
            ry = y * cp - rz * sp
            rz = y * sp + rz * cp
            depth = min(1.0, max(0.0, (rz + 1.3) / 2.6))  # 0 loin, 1 proche
            persp = 1.0 / (1.0 - 0.30 * rz)
            sx = cx + rx * radius * persp * breathe
            sy = cy - ry * radius * persp * breathe
            proj.append((sx, sy, depth))

        # Glow additif : les recouvrements s'additionnent -> lumière.
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)

        # Traits, triés du plus lointain au plus proche.
        edges = sorted(
            self.edges,
            key=lambda e: (proj[e[0]][2] + proj[e[1]][2]),
        )
        for (i, j, weight) in edges:
            xi, yi, di = proj[i]
            xj, yj, dj = proj[j]
            davg = (di + dj) / 2.0
            alpha = int(120 * weight * (0.15 + 0.85 * davg))
            if alpha <= 2:
                continue
            pen = QPen(self._depth_color(base, davg, alpha))
            pen.setWidthF(0.5 + 1.1 * davg)
            painter.setPen(pen)
            painter.drawLine(int(xi), int(yi), int(xj), int(yj))

        # Points, triés arrière -> avant, avec halo pour ceux de devant.
        painter.setPen(QColor(0, 0, 0, 0))
        for (sx, sy, depth) in sorted(proj, key=lambda p: p[2]):
            core = 1.0 + 2.4 * depth
            if depth > 0.45:  # halo lumineux à l'avant
                halo = core * 3.2
                painter.setBrush(self._depth_color(base, depth, int(26 * depth)))
                painter.drawEllipse(
                    int(sx - halo), int(sy - halo), int(halo * 2), int(halo * 2)
                )
            # Coeur : cyan clair proche du blanc à l'avant.
            r = min(255, base.red() + int(80 * depth))
            g = min(255, base.green() + int(50 * depth))
            b = min(255, base.blue() + int(20 * depth))
            painter.setBrush(QColor(r, g, b, int(120 + 135 * depth)))
            painter.drawEllipse(
                int(sx - core), int(sy - core), int(core * 2), int(core * 2)
            )

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
