from __future__ import annotations

import pathlib
import sys
import unittest

import aiohttp


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from open_workshop_telegram_bot.health import HealthProbeServer


class HealthProbeTests(unittest.IsolatedAsyncioTestCase):
    async def test_healthz_and_readyz(self) -> None:
        probe = HealthProbeServer(host="127.0.0.1", port=0)

        await probe.start()
        try:
            self.assertTrue(probe.addresses)
            host, port = probe.addresses[0]
            base_url = f"http://{host}:{port}"

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/healthz") as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(await response.json(), {"status": "ok"})

                async with session.get(f"{base_url}/readyz") as response:
                    self.assertEqual(response.status, 503)
                    self.assertEqual(
                        await response.json(),
                        {"status": "starting", "ready": False},
                    )

                probe.mark_ready()

                async with session.get(f"{base_url}/readyz") as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(
                        await response.json(),
                        {"status": "ok", "ready": True},
                    )
        finally:
            await probe.stop()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
