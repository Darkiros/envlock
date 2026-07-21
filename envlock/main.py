"""Point d'entrée d'EnvLock.

Flux :
  Panneau de contrôle  ──(Verrouiller)──▶  Écran verrouillé
        ▲                                        │
        └──────────(mot de passe correct)────────┘
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import Config
from .control_panel import ControlPanel
from .lock_window import LockWindow
from .style import QSS


class App:
    def __init__(self) -> None:
        self.config = Config.load()
        self.panel = ControlPanel(self.config)
        self.panel.lock_requested.connect(self.lock)
        self.lock_window: LockWindow | None = None

    def lock(self) -> None:
        self.panel.hide()
        self.lock_window = LockWindow(self.config)
        self.lock_window.unlocked.connect(self.unlock)
        self.lock_window.start()

    def unlock(self) -> None:
        self.lock_window = None
        # Recharge la config au cas où (mot de passe/anim modifiés ailleurs).
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def show(self) -> None:
        self.panel.show()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("EnvLock")
    app.setStyleSheet(QSS)

    controller = App()
    controller.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
