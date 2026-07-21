"""Verrouillage bas niveau : blocage clavier + inhibition de la mise en veille.

Windows : hook clavier bas niveau (WH_KEYBOARD_LL) pour avaler les combinaisons
d'évasion (Alt+Tab, touche Windows, Alt+F4, Ctrl+Échap, Ctrl+Maj+Échap...) et
SetThreadExecutionState pour empêcher l'écran/le système de se mettre en veille.

⚠️ Ctrl+Alt+Suppr (Secure Attention Sequence) ne PEUT PAS être bloqué depuis
le user-mode — c'est une protection volontaire de Windows contre les malwares.

Linux : stub pour l'instant (à implémenter plus tard via X11/Wayland).
"""
from __future__ import annotations

import os


class BaseLocker:
    def start(self) -> None:  # pragma: no cover - interface
        ...

    def stop(self) -> None:  # pragma: no cover - interface
        ...


# ----------------------------------------------------------------------
# Windows
# ----------------------------------------------------------------------
if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    WH_KEYBOARD_LL = 13
    HC_ACTION = 0
    LLKHF_ALTDOWN = 0x20

    # Codes de touches virtuelles
    VK_TAB = 0x09
    VK_ESCAPE = 0x1B
    VK_LWIN = 0x5B
    VK_RWIN = 0x5C
    VK_F4 = 0x73
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10

    # Inhibition de la veille
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002

    ULONG_PTR = ctypes.c_size_t
    LRESULT = ctypes.c_ssize_t

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", wintypes.DWORD),
            ("scanCode", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    HOOKPROC = ctypes.WINFUNCTYPE(
        LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    )

    user32.SetWindowsHookExW.restype = wintypes.HHOOK
    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD
    ]
    user32.CallNextHookEx.restype = LRESULT
    user32.CallNextHookEx.argtypes = [
        wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    ]
    user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
    user32.GetAsyncKeyState.restype = wintypes.SHORT
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

    def _is_down(vk: int) -> bool:
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)

    class WindowsLocker(BaseLocker):
        def __init__(self):
            self._hook = None
            self._proc = HOOKPROC(self._callback)  # gardé vivant

        def _callback(self, nCode, wParam, lParam):
            if nCode == HC_ACTION:
                kb = ctypes.cast(
                    lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)
                ).contents
                if self._should_block(kb):
                    return 1  # avale la frappe
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        @staticmethod
        def _should_block(kb: "KBDLLHOOKSTRUCT") -> bool:
            vk = kb.vkCode
            alt = bool(kb.flags & LLKHF_ALTDOWN)
            ctrl = _is_down(VK_CONTROL)
            shift = _is_down(VK_SHIFT)

            if vk in (VK_LWIN, VK_RWIN):  # touche Windows
                return True
            if vk == VK_TAB and alt:  # Alt+Tab
                return True
            if vk == VK_ESCAPE and (alt or ctrl):  # Alt/Ctrl+Échap
                return True
            if vk == VK_F4 and alt:  # Alt+F4
                return True
            if vk == VK_ESCAPE and ctrl and shift:  # Ctrl+Maj+Échap
                return True
            return False

        def start(self) -> None:
            if self._hook:
                return
            hmod = kernel32.GetModuleHandleW(None)
            self._hook = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL, self._proc, hmod, 0
            )
            # Empêche veille écran + système tant qu'on est verrouillé.
            kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )

        def stop(self) -> None:
            if self._hook:
                user32.UnhookWindowsHookEx(self._hook)
                self._hook = None
            kernel32.SetThreadExecutionState(ES_CONTINUOUS)

    def make_locker() -> BaseLocker:
        return WindowsLocker()

# ----------------------------------------------------------------------
# Linux / autres : stub (à compléter plus tard)
# ----------------------------------------------------------------------
else:
    class NoopLocker(BaseLocker):
        def start(self) -> None:
            print(
                "[EnvLock] Blocage clavier natif non implémenté sur cette "
                "plateforme — l'écran s'affiche mais les raccourcis système "
                "ne sont pas bloqués."
            )

        def stop(self) -> None:
            pass

    def make_locker() -> BaseLocker:
        return NoopLocker()
