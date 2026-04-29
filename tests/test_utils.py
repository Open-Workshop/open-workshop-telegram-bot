from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from open_workshop_telegram_bot.utils import is_steam_workshop_url, parse_link


class LinkParsingTests(unittest.TestCase):
    def test_detects_steam_workshop_urls(self) -> None:
        self.assertTrue(
            is_steam_workshop_url(
                "https://steamcommunity.com/sharedfiles/filedetails/?id=3701480464"
            )
        )
        self.assertTrue(
            is_steam_workshop_url(
                "https://www.steamcommunity.com/workshop/filedetails/?id=3701480464"
            )
        )

    def test_parse_link_returns_steam_workshop_id(self) -> None:
        self.assertEqual(
            parse_link(
                "https://steamcommunity.com/sharedfiles/filedetails/?id=3701480464"
            ),
            "3701480464",
        )

    def test_parse_link_returns_open_workshop_mod_id(self) -> None:
        self.assertEqual(
            parse_link(
                "https://openworkshop.miskler.ru/mod/69752?game=5",
            ),
            "69752",
        )

    def test_parse_link_returns_open_workshop_mod_id_for_any_host(self) -> None:
        self.assertEqual(
            parse_link("https://example.com/mod/69752?game=5"),
            "69752",
        )

    def test_parse_link_returns_open_workshop_api_mod_id(self) -> None:
        self.assertEqual(
            parse_link(
                "https://api.openworkshop.miskler.ru/mods/69752",
            ),
            "69752",
        )

    def test_parse_link_returns_open_workshop_api_query_id(self) -> None:
        self.assertEqual(
            parse_link(
                "https://api.openworkshop.miskler.ru/mods?id=69752",
            ),
            "69752",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
