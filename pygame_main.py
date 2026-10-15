"""Ponto de entrada da versão Pygame; as regras ficam em pygame_rpg e batalha.py."""
try:
    import pygame  # noqa: F401
except ImportError:
    raise SystemExit(
        "Pygame não está instalado. Execute: python -m pip install -r requirements.txt"
    )

from pygame_rpg.app import run


if __name__ == "__main__":
    run()
