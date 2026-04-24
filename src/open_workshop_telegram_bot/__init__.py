"""Open Workshop Telegram Bot package."""

from __future__ import annotations

__all__ = ["main", "run"]


def __getattr__(name: str):
    if name in __all__:
        from .app import main, run

        globals().update(main=main, run=run)
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
