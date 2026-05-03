from __future__ import annotations

import email.utils
import math
import re
from urllib.parse import parse_qs, urlparse


_FACTORIO_MOD_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_FACTORIO_RESERVED_NAMES = {
    "changelog",
    "dependencies",
    "discussion",
    "download",
    "downloads",
    "factorio",
    "http",
    "https",
    "information",
    "metrics",
    "mod",
    "mods",
    "openworkshop",
    "steam",
}


def _normalize_hostname(url: str | None) -> str | None:
    if not isinstance(url, str):
        return None

    hostname = urlparse(url).hostname
    if not hostname:
        return None

    hostname = hostname.lower()
    if hostname.startswith("www."):
        return hostname[4:]
    return hostname


def is_open_workshop_url(
    link: str | None,
) -> bool:
    if not isinstance(link, str):
        return False

    parsed = urlparse(link)
    if parsed.scheme not in {"http", "https"}:
        return False

    if _normalize_hostname(link) == "mods.factorio.com":
        return False

    return (
        parsed.path.startswith("/mod/")
        or parsed.path.startswith("/mods/")
        or "id" in parse_qs(parsed.query)
    )


def is_steam_workshop_url(link: str | None) -> bool:
    if not isinstance(link, str):
        return False

    parsed = urlparse(link)
    if parsed.scheme not in {"http", "https"}:
        return False

    return _normalize_hostname(link) == "steamcommunity.com" and (
        parsed.path.startswith("/sharedfiles/filedetails/")
        or parsed.path.startswith("/workshop/filedetails/")
    )


def is_factorio_workshop_url(link: str | None) -> bool:
    if not isinstance(link, str):
        return False

    parsed = urlparse(link)
    if parsed.scheme not in {"http", "https"}:
        return False

    return _normalize_hostname(link) == "mods.factorio.com" and (
        parsed.path.startswith("/mod/")
        or parsed.path.startswith("/mods/")
    )


def is_factorio_source_id(link: str | None) -> bool:
    if not isinstance(link, str):
        return False

    value = link.strip()
    if not value or value.isdigit() or "://" in value:
        return False

    if value.lower() in _FACTORIO_RESERVED_NAMES:
        return False

    return _FACTORIO_MOD_NAME_RE.fullmatch(value) is not None


def _extract_mod_id(parsed) -> str | bool:
    if parsed.path.startswith("/mod/"):
        return parsed.path.removeprefix("/mod/").split("/", 1)[0]

    if parsed.path.startswith("/mods/"):
        return parsed.path.removeprefix("/mods/").split("/", 1)[0]

    captured_value = parse_qs(parsed.query)
    try:
        return captured_value["id"][0]
    except (KeyError, IndexError):
        return False


def parse_link(
    link: str | None,
) -> str | bool:
    if not isinstance(link, str):
        return False

    if is_steam_workshop_url(link):
        parsed = urlparse(link)
        link = _extract_mod_id(parsed)

    elif is_factorio_workshop_url(link):
        parsed = urlparse(link)
        link = _extract_factorio_mod_id(parsed)

    elif is_open_workshop_url(link):
        parsed = urlparse(link)
        if parsed.path.startswith("/mod/") or parsed.path.startswith("/mods/") or "id" in parse_qs(parsed.query):
            link = _extract_mod_id(parsed)

    return link

def format_seconds(seconds: float | int, word: str = "секунда") -> str:
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return "0 секунд"

    if not math.isfinite(value):
        return "0 секунд"

    rounded = round(value)
    if math.isclose(value, rounded):
        integer_value = int(rounded)
        abs_value = abs(integer_value)
        last_two = abs_value % 100
        last_one = abs_value % 10

        if 11 <= last_two <= 14:
            unit = "секунд"
        elif last_one == 1:
            unit = "секунда"
        elif last_one in (2, 3, 4):
            unit = "секунды"
        else:
            unit = "секунд"

        return f"{integer_value} {unit}"

    return f"{value:g} секунды"


def extract_filename(header: str) -> str:
    if header.startswith("attachment; filename="):
        return header.split("attachment; filename=", 1)[-1]
    return email.utils.unquote(header.split("filename*=utf-8''", 1)[-1])


def _extract_factorio_mod_id(parsed) -> str | bool:
    path = parsed.path.strip("/")
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return False

    if segments[0] == "mod":
        candidate = segments[1] if len(segments) > 1 else ""
    elif segments[0] == "mods":
        if len(segments) == 2:
            candidate = segments[1]
        elif len(segments) == 3:
            candidate = segments[1] if segments[2] in _FACTORIO_SUBPAGES else segments[2]
        else:
            candidate = segments[-2] if segments[-1] in _FACTORIO_SUBPAGES else segments[-1]
    else:
        return False

    return candidate if candidate and _FACTORIO_MOD_NAME_RE.fullmatch(candidate) else False


_FACTORIO_SUBPAGES = {
    "changelog",
    "dependencies",
    "discussion",
    "downloads",
    "information",
    "metrics",
}
