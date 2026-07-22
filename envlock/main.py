"""Point d'entrée d'EnvLock.

Flux :
  Panneau de contrôle  ──(Verrouiller / raccourci global)──▶  Écran verrouillé
        ▲                                                          │
        └──────────────(mot de passe correct)──────────────────────┘

La fenêtre peut se réduire dans la barre de notification (systray) ; un
raccourci clavier global configurable permet de verrouiller à tout moment.
"""
from __future__ import annotations

import sys

from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .config import Config
from .control_panel import ControlPanel
from .hotkey import make_hotkey
from .lock_window import LockWindow
from .style import QSS


def app_icon() -> QIcon:
    """Petite icône « orbe » générée à la volée (aucun fichier requis)."""
    pm = QPixmap(64, 64)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QRadialGradient(26, 24, 34)
    grad.setColorAt(0.0, QColor("#a9ecff"))
    grad.setColorAt(0.6, QColor("#37b4e6"))
    grad.setColorAt(1.0, QColor("#0a2c45"))
    p.setBrush(grad)
    p.setPen(QColor("#63d0ff"))
    p.drawEllipse(6, 6, 52, 52)
    p.end()
    return QIcon(pm)


class App:
    def __init__(self) -> None:
        self.config = Config.load()
        self.icon = app_icon()

        self.panel = ControlPanel(self.config)
        self.panel.setWindowIcon(self.icon)
        self.panel.lock_requested.connect(self.request_lock)
        self.panel.hotkey_changed.connect(self.apply_hotkey)
        self.panel.minimized_to_tray.connect(self._on_minimized)
        self.panel.quit_requested.connect(self.quit_app)

        self.lock_window: LockWindow | None = None
        self._panel_was_visible = True

        self._build_tray()
        self.hotkey = make_hotkey(self.request_lock)
        self.apply_hotkey()

    # ---- barre de notification ---------------------------------------
    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.icon)
        self.tray.setToolTip("EnvLock")
        menu = QMenu()
        menu.addAction("Ouvrir le panneau", self.show_panel)
        menu.addAction("Verrouiller maintenant", self.request_lock)
        menu.addSeparator()
        menu.addAction("Quitter", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_panel()

    def _on_minimized(self) -> None:
        self.tray.showMessage(
            "EnvLock",
            "L'application continue de tourner ici. Clic droit pour verrouiller "
            "ou quitter.",
            self.icon,
            3000,
        )

    def show_panel(self) -> None:
        self.panel.showNormal()
        self.panel.raise_()
        self.panel.activateWindow()

    # ---- raccourci global --------------------------------------------
    def apply_hotkey(self) -> None:
        seq = self.config.hotkey_sequence
        if self.config.hotkey_enabled:
            ok = self.hotkey.register(seq)
        else:
            self.hotkey.unregister()
            ok = False
        self.panel.set_hotkey_status(ok, seq)

    # ---- verrouillage -------------------------------------------------
    def request_lock(self) -> None:
        if self.lock_window is not None:  # déjà verrouillé
            return
        if not self.config.has_password():
            self.show_panel()
            self.panel._feedback("Définis d'abord un mot de passe.", ok=False)
            return
        self._panel_was_visible = self.panel.isVisible()
        self.panel.hide()
        self.lock_window = LockWindow(self.config)
        self.lock_window.setWindowIcon(self.icon)
        self.lock_window.unlocked.connect(self.unlock)
        self.lock_window.start()

    def unlock(self) -> None:
        self.lock_window = None
        # On rend la main dans l'état précédent : si le panneau était réduit
        # dans la barre, on y reste ; sinon on le ré-affiche.
        if self._panel_was_visible:
            self.show_panel()

    def quit_app(self) -> None:
        self.hotkey.unregister()
        self.panel.force_quit()
        self.tray.hide()
        QApplication.quit()

    def show(self) -> None:
        self.panel.show()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("EnvLock")
    app.setQuitOnLastWindowClosed(False)  # géré via le tray
    app.setStyleSheet(QSS)

    controller = App()
    controller.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
