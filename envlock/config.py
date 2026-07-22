"""Chargement / sauvegarde de la configuration et gestion du mot de passe.

Le mot de passe n'est jamais stocké en clair : on garde uniquement un hash
PBKDF2-HMAC-SHA256 avec sel aléatoire (stdlib uniquement, aucune dépendance
à compiler — portable Windows/Linux).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

APP_NAME = "EnvLock"

# Réglages par défaut (utilisés au premier lancement).
DEFAULTS: dict[str, Any] = {
    "animation": "sphere",
    "clock": {"show": True},
    "animations": {
        "sphere": {
            "count": 800,
            "amp": 0.20,
            "wave_speed": 1.0,
            "rot_speed": 0.35,
            "dot_size": 1.7,
            "hue": 193,
            "pulse": 0.15,
            "lines": False,
            "background": "#05070d",
        },
        "particles": {
            "count": 90,
            "link_distance": 140,
            "color": "#4f9dff",
            "background": "#0a0e17",
        },
        "matrix": {
            "color": "#00ff66",
            "background": "#000000",
            "font_size": 18,
        },
        "gradient": {
            "colors": ["#5b2be0", "#2b6be0", "#e02b8a"],
            "background": "#07070d",
        },
    },
    "password": None,  # rempli par set_password()
}


def config_dir() -> Path:
    """Répertoire de config selon la plateforme."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return config_dir() / "config.json"


class Config:
    def __init__(self, data: dict[str, Any] | None = None):
        self.data = _merge(deepcopy(DEFAULTS), data or {})
        self._migrate()

    def _migrate(self) -> None:
        """Réinitialise la sphère si elle est encore à l'ancien schéma."""
        sphere = self.data.get("animations", {}).get("sphere", {})
        if "link_distance" in sphere or "speed" in sphere:
            self.data["animations"]["sphere"] = deepcopy(
                DEFAULTS["animations"]["sphere"]
            )

    # ---- persistance --------------------------------------------------
    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        if path.exists():
            try:
                return cls(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        return cls()

    def save(self) -> None:
        config_path().write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ---- accès pratique ----------------------------------------------
    @property
    def animation(self) -> str:
        return self.data.get("animation", "particles")

    @animation.setter
    def animation(self, value: str) -> None:
        self.data["animation"] = value

    def anim_options(self, name: str) -> dict[str, Any]:
        return self.data.get("animations", {}).get(name, {})

    @property
    def show_clock(self) -> bool:
        return bool(self.data.get("clock", {}).get("show", True))

    @show_clock.setter
    def show_clock(self, value: bool) -> None:
        self.data.setdefault("clock", {})["show"] = bool(value)

    # ---- mot de passe -------------------------------------------------
    def has_password(self) -> bool:
        return bool(self.data.get("password"))

    def set_password(self, plain: str) -> None:
        self.data["password"] = hash_password(plain)

    def verify_password(self, plain: str) -> bool:
        record = self.data.get("password")
        return bool(record) and verify_password(plain, record)


# ---- fonctions de hachage --------------------------------------------
def hash_password(plain: str, *, iterations: int = 200_000) -> dict[str, Any]:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iterations)
    return {
        "algo": "pbkdf2_sha256",
        "iterations": iterations,
        "salt": salt.hex(),
        "hash": digest.hex(),
    }


def verify_password(plain: str, record: dict[str, Any]) -> bool:
    try:
        salt = bytes.fromhex(record["salt"])
        expected = bytes.fromhex(record["hash"])
        iterations = int(record.get("iterations", 200_000))
    except (KeyError, ValueError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


def _merge(base: dict, override: dict) -> dict:
    """Fusion récursive : les clés manquantes gardent la valeur par défaut."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base
