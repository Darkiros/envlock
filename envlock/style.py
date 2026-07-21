"""Feuille de style Qt (thème sombre moderne)."""

QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; }

QWidget { background-color: #0e1117; color: #e6e9ef; }

QLabel#title { font-size: 34px; font-weight: 700; color: #ffffff; }
QLabel#subtitle { font-size: 14px; color: #8b93a7; }
QLabel#section { color: #808aa0; letter-spacing: 2px; }

QComboBox, QLineEdit {
    background-color: #171b24;
    border: 1px solid #262c3a;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 14px;
    color: #e6e9ef;
    selection-background-color: #3b82f6;
}
QComboBox:focus, QLineEdit:focus { border: 1px solid #3b82f6; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView {
    background-color: #171b24;
    border: 1px solid #262c3a;
    selection-background-color: #3b82f6;
    outline: none;
}

QCheckBox { spacing: 8px; font-size: 13px; color: #c3c9d6; }
QCheckBox::indicator {
    width: 18px; height: 18px; border-radius: 5px;
    border: 1px solid #3a4152; background: #171b24;
}
QCheckBox::indicator:checked { background: #3b82f6; border: 1px solid #3b82f6; }

QPushButton {
    background-color: #1c2230;
    border: 1px solid #2a3242;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 14px;
    color: #e6e9ef;
}
QPushButton:hover { background-color: #242c3d; }
QPushButton:pressed { background-color: #2c3548; }
QPushButton:disabled { color: #565f72; }

QPushButton#lockButton {
    background-color: #3b82f6; border: none; font-size: 16px; font-weight: 600;
    color: #ffffff;
}
QPushButton#lockButton:hover { background-color: #2f6fe0; }
QPushButton#lockButton:disabled { background-color: #2a3242; color: #565f72; }

QPushButton#primary {
    background-color: #3b82f6; border: none; color: #ffffff; font-weight: 600;
}
QPushButton#primary:hover { background-color: #2f6fe0; }

QFrame#preview {
    background-color: #05070c;
    border: 1px solid #262c3a;
    border-radius: 14px;
}

QFrame#card {
    background-color: rgba(20, 24, 33, 235);
    border: 1px solid #2a3242;
    border-radius: 18px;
}
/* Les enfants héritent sinon du fond opaque global -> barres noires. */
QFrame#card > QLabel { background: transparent; border: none; }
QLabel#cardTitle { font-size: 18px; font-weight: 600; color: #ffffff; }
QLabel#cardError { color: #ff5c6c; font-size: 13px; min-height: 16px; }

QLabel#pwStatus { font-size: 12px; color: #f0b429; }
QLabel#pwStatus[ok="true"] { color: #3fb950; }
QLabel#pwFeedback { font-size: 12px; color: #ff5c6c; }
QLabel#pwFeedback[ok="true"] { color: #3fb950; }
"""
