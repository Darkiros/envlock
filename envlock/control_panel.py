"""Panneau de contrôle : choix de l'animation, aperçu, mot de passe, verrouillage."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .animations import create_animation, labels
from .config import Config


class PreviewFrame(QFrame):
    """Conteneur 16:9 qui héberge l'animation d'aperçu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("preview")
        self.setFixedSize(480, 270)
        self._anim: QWidget | None = None

    def show_animation(self, key: str, options: dict) -> None:
        if self._anim is not None:
            self._anim.deleteLater()
        self._anim = create_animation(key, options, parent=self)
        self._anim.setGeometry(0, 0, self.width(), self.height())
        self._anim.show()


class ControlPanel(QWidget):
    lock_requested = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setWindowTitle("EnvLock — Panneau de contrôle")
        self.setMinimumSize(760, 560)
        self._build()
        self._refresh_preview()
        self._refresh_password_state()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        title = QLabel("EnvLock")
        title.setObjectName("title")
        subtitle = QLabel("Verrouille ton environnement — sans verrouiller Windows")
        subtitle.setObjectName("subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        # ---- ligne principale : réglages | aperçu --------------------
        row = QHBoxLayout()
        row.setSpacing(24)

        # colonne réglages
        settings = QVBoxLayout()
        settings.setSpacing(12)

        settings.addWidget(_section_label("Animation"))
        self.anim_combo = QComboBox()
        for key, label in labels():
            self.anim_combo.addItem(label, key)
        idx = self.anim_combo.findData(self.config.animation)
        if idx >= 0:
            self.anim_combo.setCurrentIndex(idx)
        self.anim_combo.currentIndexChanged.connect(self._on_anim_changed)
        settings.addWidget(self.anim_combo)

        self.clock_check = QCheckBox("Afficher l'horloge sur l'écran verrouillé")
        self.clock_check.setChecked(self.config.show_clock)
        self.clock_check.toggled.connect(self._on_clock_toggled)
        settings.addWidget(self.clock_check)

        settings.addSpacing(8)
        settings.addWidget(_section_label("Mot de passe"))
        self.pw_status = QLabel("")
        self.pw_status.setObjectName("pwStatus")
        settings.addWidget(self.pw_status)

        self.current_pw = QLineEdit()
        self.current_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_pw.setPlaceholderText("Mot de passe actuel")
        settings.addWidget(self.current_pw)

        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw.setPlaceholderText("Nouveau mot de passe")
        settings.addWidget(self.new_pw)

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw.setPlaceholderText("Confirmer le mot de passe")
        settings.addWidget(self.confirm_pw)

        save_pw = QPushButton("Enregistrer le mot de passe")
        save_pw.clicked.connect(self._save_password)
        settings.addWidget(save_pw)

        self.pw_feedback = QLabel("")
        self.pw_feedback.setObjectName("pwFeedback")
        settings.addWidget(self.pw_feedback)

        settings.addStretch(1)

        # colonne aperçu
        preview_col = QVBoxLayout()
        preview_col.setSpacing(10)
        preview_col.addWidget(_section_label("Aperçu"))
        self.preview = PreviewFrame()
        preview_col.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignTop)
        preview_col.addStretch(1)

        row.addLayout(settings, 1)
        row.addLayout(preview_col, 0)
        root.addLayout(row, 1)

        # ---- bas : bouton verrouiller --------------------------------
        self.lock_btn = QPushButton("🔒  Verrouiller maintenant")
        self.lock_btn.setObjectName("lockButton")
        self.lock_btn.setMinimumHeight(52)
        self.lock_btn.clicked.connect(self._on_lock)
        root.addWidget(self.lock_btn)

    # ------------------------------------------------------------------
    def _on_anim_changed(self) -> None:
        key = self.anim_combo.currentData()
        self.config.animation = key
        self.config.save()
        self._refresh_preview()

    def _on_clock_toggled(self, checked: bool) -> None:
        self.config.show_clock = checked
        self.config.save()

    def _refresh_preview(self) -> None:
        key = self.config.animation
        self.preview.show_animation(key, self.config.anim_options(key))

    def _refresh_password_state(self) -> None:
        has = self.config.has_password()
        self.current_pw.setVisible(has)
        self.pw_status.setText(
            "✔ Un mot de passe est défini." if has
            else "⚠ Aucun mot de passe défini — obligatoire avant de verrouiller."
        )
        self.pw_status.setProperty("ok", has)
        self.pw_status.style().unpolish(self.pw_status)
        self.pw_status.style().polish(self.pw_status)
        self.lock_btn.setEnabled(has)

    def _save_password(self) -> None:
        new = self.new_pw.text()
        confirm = self.confirm_pw.text()
        if self.config.has_password():
            if not self.config.verify_password(self.current_pw.text()):
                self._feedback("Mot de passe actuel incorrect.", ok=False)
                return
        if len(new) < 4:
            self._feedback("Le mot de passe doit faire au moins 4 caractères.", ok=False)
            return
        if new != confirm:
            self._feedback("Les deux mots de passe ne correspondent pas.", ok=False)
            return
        self.config.set_password(new)
        self.config.save()
        self.current_pw.clear()
        self.new_pw.clear()
        self.confirm_pw.clear()
        self._feedback("Mot de passe enregistré.", ok=True)
        self._refresh_password_state()

    def _feedback(self, msg: str, *, ok: bool) -> None:
        self.pw_feedback.setText(msg)
        self.pw_feedback.setProperty("ok", ok)
        self.pw_feedback.style().unpolish(self.pw_feedback)
        self.pw_feedback.style().polish(self.pw_feedback)

    def _on_lock(self) -> None:
        if not self.config.has_password():
            self._feedback("Définis d'abord un mot de passe.", ok=False)
            return
        self.lock_requested.emit()


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName("section")
    f = QFont("Segoe UI", 10)
    f.setWeight(QFont.Weight.DemiBold)
    lbl.setFont(f)
    return lbl
