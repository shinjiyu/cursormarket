"""Lightweight i18n for cursor_agent_memory.

Translation files live in ``cursor_agent_memory/locales/<code>.json``.

English (``en``) is the default and acts as the fallback for any missing key.
Other locales only need to override the keys they translate.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

DEFAULT_LOCALE = "en"
LOCALES_DIR = Path(__file__).resolve().parent / "locales"
ENV_VAR = "CURSOR_AGENT_MEMORY_LOCALE"


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, full_key))
        else:
            flat[full_key] = str(value)
    return flat


@lru_cache(maxsize=None)
def _load(locale: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return _flatten(payload)


def available_locales() -> list[str]:
    if not LOCALES_DIR.exists():
        return [DEFAULT_LOCALE]
    codes = sorted({path.stem for path in LOCALES_DIR.glob("*.json")})
    if DEFAULT_LOCALE not in codes:
        codes.insert(0, DEFAULT_LOCALE)
    return codes


def normalise(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    code = locale.strip().lower().replace("_", "-")
    if not code:
        return DEFAULT_LOCALE
    short = code.split("-", 1)[0]
    supported = set(available_locales())
    if code in supported:
        return code
    if short in supported:
        return short
    return DEFAULT_LOCALE


def parse_accept_language(header: str | None) -> list[str]:
    if not header:
        return []
    items: list[tuple[float, str]] = []
    for part in header.split(","):
        chunk = part.strip()
        if not chunk:
            continue
        if ";" in chunk:
            value, _, q_part = chunk.partition(";")
            quality = 1.0
            for piece in q_part.split(";"):
                piece = piece.strip()
                if piece.startswith("q="):
                    try:
                        quality = float(piece[2:])
                    except ValueError:
                        quality = 0.0
            items.append((quality, value.strip().lower()))
        else:
            items.append((1.0, chunk.lower()))
    items.sort(key=lambda x: x[0], reverse=True)
    return [code for _, code in items if code and code != "*"]


def _match(code: str | None, supported: set[str]) -> str | None:
    if not code:
        return None
    raw = code.strip().lower().replace("_", "-")
    if not raw:
        return None
    if raw in supported:
        return raw
    short = raw.split("-", 1)[0]
    if short in supported:
        return short
    return None


def resolve_locale(
    *,
    requested: str | None = None,
    session: str | None = None,
    accept_language: str | None = None,
    env: str | None = None,
) -> str:
    """Pick the best locale code given multiple signals."""
    supported = set(available_locales())
    for candidate in (requested, session, env):
        match = _match(candidate, supported)
        if match:
            return match
    for code in parse_accept_language(accept_language):
        match = _match(code, supported)
        if match:
            return match
    return DEFAULT_LOCALE


def translate(key: str, locale: str | None = None, /, **variables: Any) -> str:
    """Look up ``key`` in ``locale``; fall back to English; finally return the key."""
    code = normalise(locale)
    primary = _load(code)
    template = primary.get(key)
    if template is None and code != DEFAULT_LOCALE:
        template = _load(DEFAULT_LOCALE).get(key)
    if template is None:
        template = key
    if not variables:
        return template
    try:
        return template.format(**variables)
    except (KeyError, IndexError, ValueError):
        return template


def make_translator(locale: str | None) -> Any:
    """Return a callable bound to ``locale`` for templates."""
    code = normalise(locale)

    def _t(key: str, **variables: Any) -> str:
        return translate(key, code, **variables)

    return _t


def env_locale(default: str = DEFAULT_LOCALE) -> str:
    """Return the locale from the env var, falling back to ``default``."""
    return normalise(os.environ.get(ENV_VAR, default))


def reload_translations() -> None:
    """Drop cached locale data (useful for tests)."""
    _load.cache_clear()


def supported_locale_labels() -> list[tuple[str, str]]:
    """Return ``[(code, label)]`` pairs for UI language pickers."""
    pairs: list[tuple[str, str]] = []
    for code in available_locales():
        label = translate("language.name", code)
        if label == "language.name":
            label = code
        pairs.append((code, label))
    return pairs


__all__: Iterable[str] = (
    "DEFAULT_LOCALE",
    "ENV_VAR",
    "available_locales",
    "env_locale",
    "make_translator",
    "normalise",
    "parse_accept_language",
    "reload_translations",
    "resolve_locale",
    "supported_locale_labels",
    "translate",
)
