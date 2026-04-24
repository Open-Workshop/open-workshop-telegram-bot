from __future__ import annotations

import email.utils
from functools import lru_cache
from urllib.parse import parse_qs, urlparse

import pymorphy2


def parse_link(link: str | None) -> str | bool:
    if not isinstance(link, str):
        return False

    if link.startswith("https://steamcommunity.com/sharedfiles/filedetails/") or link.startswith(
        "https://steamcommunity.com/workshop/filedetails/"
    ) or link.startswith("https://openworkshop.su/mod/"):
        parsed = urlparse(link, "highlight=params#url-parsing")

        try:
            if parsed.path.startswith("/mod/"):
                link = parsed.path.removeprefix("/mod/")
            else:
                captured_value = parse_qs(parsed.query)
                link = captured_value["id"][0]
        except (KeyError, IndexError):
            link = False

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
