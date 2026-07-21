"""Fenêtre de verrouillage plein écran."""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    Qt,
    QTime,
    QTimer,
    Signal,
)
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .animations import create_animation
from .config import Config
from .platform_lock import make_locker


class LockWindow(QWidget):
    unlocked = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._locker = make_locker()
        self._unlocking = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setCursor(Qt.CursorShape.BlankCursor)

        # --- fond animé -------------------------------------------------
        self.anim = create_animation(
            self.config.animation,
            self.config.anim_options(self.config.animation),
            parent=self,
        )
        self.anim.lower()

        # --- horloge ----------------------------------------------------
        self.clock = QLabel(self)
        self.clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock.setObjectName("clock")
        self.clock.setStyleSheet(
            "color: rgba(255,255,255,235); background: transparent;"
        )
        cf = QFont("Segoe UI", 64)
        cf.setWeight(QFont.Weight.Light)
        self.clock.setFont(cf)
        self.clock.setVisible(self.config.show_clock)

        self.date = QLabel(self)
        self.date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date.setStyleSheet("color: rgba(255,255,255,160); background: transparent;")
        self.date.setFont(QFont("Segoe UI", 18))
        self.date.setVisible(self.config.show_clock)

        # --- indice -----------------------------------------------------
        self.hint = QLabel("Appuyez sur Entrée pour déverrouiller", self)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setStyleSheet(
            "color: rgba(255,255,255,140); background: transparent;"
            "letter-spacing: 2px;"
        )
        self.hint.setFont(QFont("Segoe UI", 13))

        # --- carte mot de passe ----------------------------------------
        self._build_password_card()
        self.card.setVisible(False)

        # --- horloge live ----------------------------------------------
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    # ------------------------------------------------------------------
    def _build_password_card(self) -> None:
        self.card = QFrame(self)
        self.card.setObjectName("card")
        self.card.setFixedSize(420, 250)

        title = QLabel("Environnement verrouillé")
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_input.setPlaceholderText("Mot de passe")
        self.pw_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pw_input.returnPressed.connect(self._try_unlock)
        self.pw_input.installEventFilter(self)

        self.error = QLabel("")
        self.error.setObjectName("cardError")
        self.error.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ok = QPushButton("Déverrouiller")
        ok.setObjectName("primary")
        ok.clicked.connect(self._try_unlock)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self._hide_card)

        buttons = QHBoxLayout()
        buttons.addWidget(cancel)
        buttons.addWidget(ok)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(self.pw_input)
        layout.addWidget(self.error)
        layout.addLayout(buttons)

    # ------------------------------------------------------------------
    def start(self) -> None:
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self._locker.start()
        self.setFocus()

    def _update_clock(self) -> None:
        now = QTime.currentTime()
        self.clock.setText(now.toString("HH:mm"))
        from PySide6.QtCore import QDate

        self.date.setText(QDate.currentDate().toString("dddd d MMMM yyyy"))

    # ---- gestion clavier ---------------------------------------------
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        # Échap depuis le champ mot de passe -> referme la carte.
        if obj is self.pw_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._hide_card()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not self.card.isVisible():
                self._show_card()
                return
        if key == Qt.Key.Key_Escape and self.card.isVisible():
            self._hide_card()
            return
        super().keyPressEvent(event)

    def _show_card(self) -> None:
        self.error.setText("")
        self.pw_input.clear()
        self.card.setVisible(True)
        self.card.raise_()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.pw_input.setFocus()

    def _hide_card(self) -> None:
        self.card.setVisible(False)
        self.pw_input.clear()
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.setFocus()

    def _try_unlock(self) -> None:
        if self.config.verify_password(self.pw_input.text()):
            self._do_unlock()
        else:
            self.error.setText("Mot de passe incorrect")
            self.pw_input.clear()
            self._shake()

    def _shake(self) -> None:
        anim = QPropertyAnimation(self.card, b"pos", self)
        start = self.card.pos()
        anim.setDuration(320)
        anim.setKeyValueAt(0.0, start)
        anim.setKeyValueAt(0.2, start + _dx(-14))
        anim.setKeyValueAt(0.4, start + _dx(12))
        anim.setKeyValueAt(0.6, start + _dx(-8))
        anim.setKeyValueAt(0.8, start + _dx(4))
        anim.setKeyValueAt(1.0, start)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._shake_anim = anim

    def _do_unlock(self) -> None:
        self._unlocking = True
        self._locker.stop()
        self.unlocked.emit()
        self.close()

    # ---- positionnement manuel des overlays --------------------------
    def resizeEvent(self, event) -> None:  # noqa: N802
        w, h = self.width(), self.height()
        self.anim.setGeometry(0, 0, w, h)
        self.clock.setGeometry(0, int(h * 0.28), w, 90)
        self.date.setGeometry(0, int(h * 0.28) + 96, w, 30)
        self.hint.setGeometry(0, h - 80, w, 24)
        self.card.move((w - self.card.width()) // 2, (h - self.card.height()) // 2)
        super().resizeEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        # Empêche toute fermeture tant qu'on n'a pas déverrouillé.
        if self._unlocking:
            self._locker.stop()
            event.accept()
        else:
            event.ignore()


def _dx(px: int):
    from PySide6.QtCore import QPoint

    return QPoint(px, 0)
