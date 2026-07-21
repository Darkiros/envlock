# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller pour EnvLock.

Build :  pyinstaller EnvLock.spec
Sortie : dist/EnvLock.exe   (un seul fichier, sans console)
"""

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "envlock.animations.particles",
        "envlock.animations.matrix",
        "envlock.animations.gradient",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Modules Qt inutiles -> binaire plus léger.
        "PySide6.QtNetwork",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtWebEngineCore",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtSql",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="EnvLock",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # pas de fenêtre console (app graphique)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/envlock.ico" if __import__("os").path.exists("assets/envlock.ico") else None,
)
