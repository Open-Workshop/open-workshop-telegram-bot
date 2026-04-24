from __future__ import annotations

import email.utils
from functools import lru_cache
from urllib.parse import parse_qs, urlparse

import pymorphy2


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


def is_open_workshop_url(link: str | None, website_address: str | None = None) -> bool:
    if not isinstance(link, str) or not isinstance(website_address, str):
        return False

    parsed = urlparse(link)
    return parsed.scheme in {"http", "https"} and _normalize_hostname(link) == _normalize_hostname(website_address)


def _extract_mod_id(parsed) -> str | bool:
    if parsed.path.startswith("/mod/"):
        return parsed.path.removeprefix("/mod/").split("/", 1)[0]

    captured_value = parse_qs(parsed.query)
    try:
        return captured_value["id"][0]
    except (KeyError, IndexError):
        return False


def parse_link(link: str | None, website_address: str | None = None) -> str | bool:
    if not isinstance(link, str):
        return False

    if link.startswith("https://steamcommunity.com/sharedfiles/filedetails/") or link.startswith(
        "https://steamcommunity.com/workshop/filedetails/"
    ):
        parsed = urlparse(link)
        link = _extract_mod_id(parsed)

    elif is_open_workshop_url(link, website_address):
        parsed = urlparse(link)
        if parsed.path.startswith("/mod/") or "id" in parse_qs(parsed.query):
            link = _extract_mod_id(parsed)

    return link


@lru_cache(maxsize=1)
def _get_morph() -> pymorphy2.MorphAnalyzer:
    return pymorphy2.MorphAnalyzer()


def format_seconds(seconds: float | int, word: str = "секунда") -> str:
    try:
        parsed_word = _get_morph().parse(word)[0]
        return f"{seconds} {parsed_word.make_agree_with_number(seconds).word}"
    except Exception:
        return "ERROR"


def extract_filename(header: str) -> str:
    if header.startswith("attachment; filename="):
        return header.split("attachment; filename=", 1)[-1]
    return email.utils.unquote(header.split("filename*=utf-8''", 1)[-1])
