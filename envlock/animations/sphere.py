"""Animation « orbe de particules » façon JARVIS.

Des particules réparties sur une sphère (spirale de Fibonacci) sont déplacées
radialement par des vagues (déplacement pseudo-ondulatoire), le tout en rotation
lente avec une légère pulsation « d'écoute ». Rendu en blending additif (glow)
avec dégradé de profondeur cyan. Portage direct de l'aperçu navigateur.

Réglages (config → animations.sphere) :
    count       nombre de particules
    amp         amplitude des vagues
    wave_speed  vitesse des vagues
    rot_speed   vitesse de rotation (rad/s)
    dot_size    taille de base des points
    hue         teinte (0-360, 193 = cyan)
    pulse       intensité de la pulsation d'écoute
    lines       True pour superposer un maillage plexus
    background  couleur de fond
"""
from __future__ import annotations

import math
import random

from PySide6.QtGui import QColor, QPainter, QPen

from .base import BaseAnimation


class SphereAnimation(BaseAnimation):
    key = "sphere"
    label = "Orbe de particules"

    def seed(self) -> None:
        count = int(self.options.get("count", 800))
        if min(self.width(), self.height()) < 260:  # aperçu plus léger
            count = max(300, count // 2)

        self.pts: list[tuple[float, float, float, float]] = []
        ga = math.pi * (3.0 - math.sqrt(5.0))  # angle d'or
        for i in range(count):
            y = 1 - (i / max(1, count - 1)) * 2
            r = math.sqrt(max(0.0, 1 - y * y))
            theta = ga * i
            self.pts.append(
                (math.cos(theta) * r, y, math.sin(theta) * r, random.uniform(0, 6.283))
            )

        # Maillage optionnel (distances conservées par la rotation).
        self.edges: list[tuple[int, int, float]] = []
        if bool(self.options.get("lines", False)):
            link = 0.34
            n = len(self.pts)
            for i in range(n):
                ax, ay, az, _ = self.pts[i]
                for j in range(i + 1, n):
                    bx, by, bz, _ = self.pts[j]
                    d = math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)
                    if d < link:
                        self.edges.append((i, j, 1.0 - d / link))

    def render_frame(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), self.bg_color("#05070d"))

        hue = float(self.options.get("hue", 193)) / 360.0
        amp = float(self.options.get("amp", 0.20))
        ws = float(self.options.get("wave_speed", 1.0))
        rot = float(self.options.get("rot_speed", 0.35))
        dot = float(self.options.get("dot_size", 1.7))
        pulse_amt = float(self.options.get("pulse", 0.15))

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) * 0.34
        size_scale = max(0.8, min(w, h) / 800.0)

        t = self._frame / 30.0  # secondes (~30 fps)
        yaw = t * rot
        pitch = 0.40 + 0.08 * math.sin(t * 0.3)
        cyw, syw = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        pulse = 1.0 + pulse_amt * max(0.0, math.sin(t * 1.3)) * (
            0.6 + 0.4 * math.sin(t * 0.5)
        )

        # Projection.
        proj = []
        for (x0, y0, z0, ph) in self.pts:
            n = (
                0.6 * math.sin(4 * y0 + t * ws)
                + 0.4 * math.cos(5 * x0 - t * ws * 0.8)
                + 0.5 * math.sin(6 * z0 + t * ws * 1.3)
            )
            rr = 1.0 + amp * n * pulse
            x, y, z = x0 * rr, y0 * rr, z0 * rr
            rx = x * cyw + z * syw
            rz = -x * syw + z * cyw
            ry = y * cp - rz * sp
            rz = y * sp + rz * cp
            depth = min(1.0, max(0.0, (rz + 1.4) / 2.8))
            persp = 1.0 / (1.0 - 0.30 * rz)
            sx = cx + rx * radius * persp
            sy = cy - ry * radius * persp
            proj.append((sx, sy, depth, ph))

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)

        # Maillage éventuel (arrière -> avant).
        if self.edges:
            for (i, j, weight) in sorted(
                self.edges, key=lambda e: proj[e[0]][2] + proj[e[1]][2]
            ):
                xi, yi, di, _ = proj[i]
                xj, yj, dj, _ = proj[j]
                dav = (di + dj) / 2.0
                alpha = 0.5 * weight * (0.1 + 0.9 * dav)
                if alpha < 0.02:
                    continue
                pen = QPen(QColor.fromHslF(hue, 0.9, min(1.0, 0.45 + dav * 0.35), alpha))
                pen.setWidthF(0.5 + dav * 0.9)
                painter.setPen(pen)
                painter.drawLine(int(xi), int(yi), int(xj), int(yj))

        # Particules (arrière -> avant pour un empilement correct).
        painter.setPen(QColor(0, 0, 0, 0))
        for (sx, sy, depth, ph) in sorted(proj, key=lambda p: p[2]):
            tw = 0.75 + 0.25 * math.sin(t * 3 + ph)
            alpha = (0.12 + 0.88 * depth) * tw
            light = min(1.0, 0.52 + depth * 0.38)
            painter.setBrush(QColor.fromHslF(hue, 1.0, light, min(1.0, alpha)))
            s = (0.6 + dot * depth) * size_scale
            painter.drawEllipse(
                int(sx - s), int(sy - s), int(s * 2), int(s * 2)
            )

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
