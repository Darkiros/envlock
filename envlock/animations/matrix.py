"""Animation « Matrix rain » : pluie de caractères."""
from __future__ import annotations

import random

from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter

from .base import BaseAnimation

_CHARS = "0123456789ABCDEFｦｧｨｩｪｫｬｭｮｯｱｲｳｴｵｶｷｸｹｺｻｼｽｾﾀﾁﾂﾃﾄﾅ$#%&@*+="


class MatrixAnimation(BaseAnimation):
    key = "matrix"
    label = "Matrix rain"

    def _font(self) -> QFont:
        size = int(self.options.get("font_size", 18))
        # Réduit la police en petit aperçu.
        if self.height() < 200:
            size = max(9, size // 2)
        f = QFont("Consolas")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPixelSize(size)
        return f

    def seed(self) -> None:
        self.font_obj = self._font()
        fm = QFontMetrics(self.font_obj)
        self.cell_w = max(6, fm.horizontalAdvance("M"))
        self.cell_h = max(8, fm.height())
        cols = max(1, self.width() // self.cell_w)
        self.drops = [random.randint(-40, 0) for _ in range(cols)]
        self.speeds = [random.choice([1, 1, 1, 2]) for _ in range(cols)]

    def advance(self) -> None:
        rows = max(1, self.height() // self.cell_h)
        for i in range(len(self.drops)):
            self.drops[i] += self.speeds[i]
            if self.drops[i] * 1 > rows + random.randint(4, 30):
                self.drops[i] = random.randint(-20, 0)
                self.speeds[i] = random.choice([1, 1, 1, 2])

    def render_frame(self, painter: QPainter) -> None:
        if self._frame < 3:
            painter.fillRect(self.rect(), QColor("#000000"))  # fond opaque au départ
        # Léger voile pour créer la traînée.
        painter.fillRect(self.rect(), QColor(0, 0, 0, 60))
        painter.setFont(self.font_obj)
        base = QColor(self.options.get("color", "#00ff66"))
        trail = 12
        for i, head in enumerate(self.drops):
            x = i * self.cell_w
            for t in range(trail):
                row = head - t
                if row < 0:
                    continue
                y = row * self.cell_h + self.cell_h
                if y > self.height() + self.cell_h:
                    continue
                ch = random.choice(_CHARS)
                if t == 0:
                    painter.setPen(QColor(220, 255, 220))  # tête brillante
                else:
                    alpha = int(230 * (1 - t / trail))
                    painter.setPen(QColor(base.red(), base.green(), base.blue(), alpha))
                painter.drawText(x, y, ch)
