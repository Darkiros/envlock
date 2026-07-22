"""Raccourci clavier global configurable (verrouillage).

Windows : RegisterHotKey + filtre d'événements natif Qt qui intercepte WM_HOTKEY.
Fonctionne même quand l'appli est réduite dans la barre de notification.

Linux : stub (à implémenter plus tard).
"""
from __future__ import annotations

import os

WM_HOTKEY = 0x0312
_HOTKEY_ID = 0xB001

# Bits de modificateurs Qt (indépendants de la version, on évite les enums).
_QT_SHIFT = 0x02000000
_QT_CTRL = 0x04000000
_QT_ALT = 0x08000000
_QT_META = 0x10000000
_QT_KEYMASK = 0x01FFFFFF


class BaseHotkey:
    def register(self, sequence: str) -> bool:  # pragma: no cover - interface
        return False

    def unregister(self) -> None:  # pragma: no cover - interface
        ...


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    from PySide6.QtCore import QAbstractNativeEventFilter
    from PySide6.QtGui import QKeySequence
    from PySide6.QtWidgets import QApplication

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.RegisterHotKey.argtypes = [
        wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT
    ]
    user32.UnregisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]

    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000

    # Touches non alphanumériques : entier Qt -> code virtuel Windows.
    _QT_F1 = 0x01000030
    _SPECIAL = {
        0x20: 0x20,          # Espace
        0x01000010: 0x24,    # Home
        0x01000011: 0x23,    # End
        0x01000016: 0x21,    # PageUp
        0x01000017: 0x22,    # PageDown
        0x01000006: 0x2D,    # Insert
        0x01000007: 0x2E,    # Delete
    }

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt_x", wintypes.LONG),
            ("pt_y", wintypes.LONG),
        ]

    def _vk_from_qtkey(key: int):
        if 0x30 <= key <= 0x39 or 0x41 <= key <= 0x5A:  # 0-9, A-Z
            return key
        if _QT_F1 <= key <= _QT_F1 + 23:                # F1-F24
            return 0x70 + (key - _QT_F1)
        return _SPECIAL.get(key)

    def _parse(sequence: str):
        ks = QKeySequence(sequence)
        if ks.count() == 0:
            return None
        item = ks[0]
        combo = item.toCombined() if hasattr(item, "toCombined") else int(item)
        key = combo & _QT_KEYMASK
        vk = _vk_from_qtkey(key)
        if vk is None:
            return None
        mods = MOD_NOREPEAT
        if combo & _QT_CTRL:
            mods |= MOD_CONTROL
        if combo & _QT_ALT:
            mods |= MOD_ALT
        if combo & _QT_SHIFT:
            mods |= MOD_SHIFT
        if combo & _QT_META:
            mods |= MOD_WIN
        return mods, vk

    class WindowsHotkey(BaseHotkey, QAbstractNativeEventFilter):
        def __init__(self, callback):
            QAbstractNativeEventFilter.__init__(self)
            self._callback = callback
            self._registered = False
            self._installed = False

        def register(self, sequence: str) -> bool:
            self.unregister()
            parsed = _parse(sequence)
            if not parsed:
                return False
            mods, vk = parsed
            if not self._installed:
                QApplication.instance().installNativeEventFilter(self)
                self._installed = True
            self._registered = bool(
                user32.RegisterHotKey(None, _HOTKEY_ID, mods, vk)
            )
            return self._registered

        def unregister(self) -> None:
            if self._registered:
                user32.UnregisterHotKey(None, _HOTKEY_ID)
                self._registered = False

        def nativeEventFilter(self, eventType, message):  # noqa: N802
            if self._registered and eventType == b"windows_generic_MSG":
                msg = MSG.from_address(int(message))
                if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                    self._callback()
            return (False, 0)

    def make_hotkey(callback) -> BaseHotkey:
        return WindowsHotkey(callback)

else:
    class NoopHotkey(BaseHotkey):
        def __init__(self, callback):
            self._callback = callback

    def make_hotkey(callback) -> BaseHotkey:
        return NoopHotkey(callback)
