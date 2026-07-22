"""Panneau de contrôle : choix de l'animation, aperçu, mot de passe, verrouillage."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QKeySequenceEdit,
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
            # Ordre important : couper le timer, détacher, PUIS supprimer,
            # sinon un tick peut arriver sur un widget en destruction (crash).
            self._anim.stop()
            self._anim.hide()
            self._anim.setParent(None)
            self._anim.deleteLater()
            self._anim = None
        self._anim = create_animation(key, options, parent=self)
        self._anim.setGeometry(0, 0, self.width(), self.height())
        self._anim.show()


class ControlPanel(QWidget):
    lock_requested = Signal()
    hotkey_changed = Signal()
    minimized_to_tray = Signal()
    quit_requested = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._force_quit = False
        self.setWindowTitle("EnvLock — Panneau de contrôle")
        self.setMinimumSize(760, 620)
        self._build()
        self._refresh_preview()
        self._refresh_password_state()

    def force_quit(self) -> None:
        """Autorise la vraie fermeture (depuis le menu Quitter du tray)."""
        self._force_quit = True

    def closeEvent(self, event) -> None:  # noqa: N802
        # Fermer la fenêtre = réduire dans la barre (sauf Quitter explicite).
        if self._force_quit:
            event.accept()
        elif self.config.minimize_to_tray:
            event.ignore()
            self.hide()
            self.minimized_to_tray.emit()
        else:
            # Tray désactivé : fermer la fenêtre quitte réellement l'appli.
            event.ignore()
            self.quit_requested.emit()

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
        settings.addWidget(_section_label("Raccourci de verrouillage"))
        self.hotkey_check = QCheckBox("Activer le raccourci global")
        self.hotkey_check.setChecked(self.config.hotkey_enabled)
        self.hotkey_check.toggled.connect(self._on_hotkey_toggled)
        settings.addWidget(self.hotkey_check)

        hk_row = QHBoxLayout()
        self.hotkey_edit = QKeySequenceEdit(QKeySequence(self.config.hotkey_sequence))
        if hasattr(self.hotkey_edit, "setMaximumSequenceLength"):
            self.hotkey_edit.setMaximumSequenceLength(1)  # une seule combinaison
        self.hotkey_edit.editingFinished.connect(self._on_hotkey_edited)
        self.hotkey_edit.setEnabled(self.config.hotkey_enabled)
        hk_row.addWidget(self.hotkey_edit, 1)
        clear_hk = QPushButton("Effacer")
        clear_hk.clicked.connect(self.hotkey_edit.clear)
        hk_row.addWidget(clear_hk)
        settings.addLayout(hk_row)
        self.hotkey_feedback = QLabel("")
        self.hotkey_feedback.setObjectName("pwStatus")
        settings.addWidget(self.hotkey_feedback)

        self.tray_check = QCheckBox("Réduire dans la barre au lieu de quitter")
        self.tray_check.setChecked(self.config.minimize_to_tray)
        self.tray_check.toggled.connect(self._on_tray_toggled)
        settings.addWidget(self.tray_check)

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

    def _on_hotkey_toggled(self, checked: bool) -> None:
        self.config.hotkey_enabled = checked
        self.config.save()
        self.hotkey_edit.setEnabled(checked)
        self.hotkey_changed.emit()

    def _on_hotkey_edited(self) -> None:
        seq = self.hotkey_edit.keySequence().toString()
        self.config.hotkey_sequence = seq
        self.config.save()
        self.hotkey_changed.emit()

    def set_hotkey_status(self, ok: bool, sequence: str) -> None:
        """Retour visuel après (dés)enregistrement du raccourci (appelé par l'app)."""
        if not self.config.hotkey_enabled:
            self.hotkey_feedback.setText("Raccourci désactivé.")
            good = False
        elif ok:
            self.hotkey_feedback.setText(f"Raccourci actif : {sequence}")
            good = True
        else:
            self.hotkey_feedback.setText(
                "Impossible d'enregistrer ce raccourci (déjà pris ?)."
            )
            good = False
        self.hotkey_feedback.setProperty("ok", good)
        self.hotkey_feedback.style().unpolish(self.hotkey_feedback)
        self.hotkey_feedback.style().polish(self.hotkey_feedback)

    def _on_tray_toggled(self, checked: bool) -> None:
        self.config.minimize_to_tray = checked
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
