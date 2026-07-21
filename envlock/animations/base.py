"""Classe de base commune aux animations.

Une animation est un QWidget qui se redessine à ~30 fps via un QTimer.
La même classe sert à la fois pour l'aperçu (petit) et pour l'écran de
verrouillage (plein écran).
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class BaseAnimation(QWidget):
    #: identifiant technique (clé de config)
    key: str = "base"
    #: nom affiché dans le panneau
    label: str = "Base"

    def __init__(self, options: dict[str, Any] | None = None, parent=None):
        super().__init__(parent)
        self.options = options or {}
        self._seeded = False
        self._frame = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 fps

    # ---- cycle de vie ------------------------------------------------
    def stop(self) -> None:
        """Arrête le timer AVANT toute destruction (évite qu'un tick se
        déclenche sur un widget en cours de suppression -> crash natif)."""
        self._timer.stop()

    def _tick(self) -> None:
        if not self._seeded and self.width() > 1 and self.height() > 1:
            self.seed()
            self._seeded = True
        if self._seeded:
            self.advance()
            self._frame += 1
            self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt)
        # Re-sème quand la taille change vraiment (préview -> plein écran).
        self._seeded = False
        super().resizeEvent(event)

    # ---- à surcharger -------------------------------------------------
    def seed(self) -> None:
        """Initialise l'état en fonction de la taille courante."""

    def advance(self) -> None:
        """Fait avancer l'animation d'une frame."""

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt)
        # Une exception dans un override Qt (paintEvent) peut faire planter
        # l'application entière : on la contient donc systématiquement.
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.render_frame(painter)
        except Exception:  # noqa: BLE001
            pass
        finally:
            painter.end()

    def render_frame(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), QColor("#000000"))

    # ---- utilitaire ---------------------------------------------------
    def bg_color(self, default: str = "#000000") -> QColor:
        return QColor(self.options.get("background", default))
