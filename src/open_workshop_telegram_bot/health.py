from __future__ import annotations

import logging

from aiohttp import web


LOGGER = logging.getLogger(__name__)


class HealthProbeServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8088) -> None:
        self._host = host
        self._port = port
        self._ready = False
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def addresses(self) -> list[tuple[str, int]]:
        if self._runner is None:
            return []
        return list(self._runner.addresses)

    async def start(self) -> None:
        if self._runner is not None:
            return

        app = web.Application()
        app.router.add_get("/healthz", self._handle_healthz)
        app.router.add_get("/readyz", self._handle_readyz)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, host=self._host, port=self._port)
        await site.start()

        self._runner = runner
        self._site = site
        LOGGER.info("Health probe started on %s", self.addresses)

    async def stop(self) -> None:
        self._ready = False
        if self._runner is None:
            return

        await self._runner.cleanup()
        self._runner = None
        self._site = None

    def mark_ready(self) -> None:
        self._ready = True

    def mark_not_ready(self) -> None:
        self._ready = False

    async def _handle_healthz(self, request: web.Request) -> web.Response:
        _ = request
        return web.json_response({"status": "ok"})

    async def _handle_readyz(self, request: web.Request) -> web.Response:
        _ = request
        if self._ready:
            return web.json_response({"status": "ok", "ready": True})
        return web.json_response({"status": "starting", "ready": False}, status=503)
