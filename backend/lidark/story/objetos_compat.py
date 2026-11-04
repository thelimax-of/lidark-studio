"""Normalização de texto compartilhada pelo registro e pelo roteirista do motor quadro."""
from __future__ import annotations

import unicodedata
from typing import Any


def plain(t: Any) -> str:
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower().strip()
