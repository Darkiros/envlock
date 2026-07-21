"""Registre des animations disponibles."""
from __future__ import annotations

from typing import Any

from .base import BaseAnimation
from .gradient import GradientAnimation
from .matrix import MatrixAnimation
from .particles import ParticlesAnimation
from .sphere import SphereAnimation

# Ordre = ordre d'affichage dans le panneau.
ANIMATIONS: dict[str, type[BaseAnimation]] = {
    SphereAnimation.key: SphereAnimation,
    ParticlesAnimation.key: ParticlesAnimation,
    MatrixAnimation.key: MatrixAnimation,
    GradientAnimation.key: GradientAnimation,
}


def create_animation(key: str, options: dict[str, Any] | None = None, parent=None) -> BaseAnimation:
    cls = ANIMATIONS.get(key, ParticlesAnimation)
    return cls(options=options, parent=parent)


def labels() -> list[tuple[str, str]]:
    """Liste (clé, libellé) pour peupler l'UI."""
    return [(k, cls.label) for k, cls in ANIMATIONS.items()]
