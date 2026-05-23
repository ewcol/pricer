import importlib
import asyncio
import os
import sys
import types
import unittest
from unittest import mock


class _NoopRoute:
    def __init__(self, *args, **kwargs):
        pass


class _FakeFastAPI:
    def __init__(self, *args, **kwargs):
        self.middlewares = []
        self.post_routes = []
        self.get_routes = []
        self.mounted = []

    def middleware(self, kind):
        def decorator(func):
            self.middlewares.append((kind, func))
            return func

        return decorator

    def post(self, path):
        def decorator(func):
            self.post_routes.append(path)
            return func

        return decorator

    def get(self, path, include_in_schema=True):
        def decorator(func):
            self.get_routes.append(path)
            return func

        return decorator

    def mount(self, *args, **kwargs):
        self.mounted.append((args, kwargs))


class _FakeX402Server:
    def __init__(self, *args, **kwargs):
        self.register_calls = []

    def register(self, *args, **kwargs):
        self.register_calls.append((args, kwargs))


def load_server_module():
    fake_fastapi = types.ModuleType("fastapi")
    fake_fastapi.FastAPI = _FakeFastAPI
    fake_fastapi.Request = _NoopRoute

    fake_responses = types.ModuleType("fastapi.responses")
    fake_responses.FileResponse = _NoopRoute
    fake_responses.StreamingResponse = _NoopRoute

    fake_staticfiles = types.ModuleType("fastapi.staticfiles")
    fake_staticfiles.StaticFiles = _NoopRoute

    fake_uvicorn = types.ModuleType("uvicorn")
    fake_uvicorn.run = lambda *args, **kwargs: None

    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None

    fake_pydantic = types.ModuleType("pydantic")

    class _BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    fake_pydantic.BaseModel = _BaseModel

    fake_x402 = types.ModuleType("x402")
    fake_x402.x402ResourceServer = lambda *args, **kwargs: _FakeX402Server()

    fake_x402_http = types.ModuleType("x402.http")
    fake_x402_http.HTTPFacilitatorClient = _NoopRoute

    fake_x402_http_middleware_fastapi = types.ModuleType("x402.http.middleware.fastapi")

    captured = {}

    def payment_middleware(*, routes, server):
        captured["routes"] = routes
        captured["server"] = server

        async def _handler(request, call_next):
            return await call_next(request)

        return _handler

    fake_x402_http_middleware_fastapi.payment_middleware = payment_middleware

    fake_x402_mechanisms_evm_exact = types.ModuleType("x402.mechanisms.evm.exact")
    fake_x402_mechanisms_evm_exact.ExactEvmServerScheme = _NoopRoute

    fake_agent = types.ModuleType("agent")
    fake_agent.run_agent = lambda *args, **kwargs: None
    fake_agent.run_agent_stream = lambda *args, **kwargs: None

    fake_clickhouse = types.ModuleType("clickhouse_client")
    fake_clickhouse.insert_item = lambda *args, **kwargs: None
    fake_clickhouse.get_all_items = lambda *args, **kwargs: []
    fake_clickhouse.get_price_history = lambda *args, **kwargs: []
    fake_clickhouse.get_portfolio_summary = lambda *args, **kwargs: {}

    fake_monitor = types.ModuleType("monitor")
    fake_monitor.schedule_item_check = lambda *args, **kwargs: "scheduled"
    fake_monitor.cancel_item_check = lambda *args, **kwargs: "canceled"

    with mock.patch.dict(
        sys.modules,
        {
            "fastapi": fake_fastapi,
            "fastapi.responses": fake_responses,
            "fastapi.staticfiles": fake_staticfiles,
            "uvicorn": fake_uvicorn,
            "dotenv": fake_dotenv,
            "pydantic": fake_pydantic,
            "x402": fake_x402,
            "x402.http": fake_x402_http,
            "x402.http.middleware.fastapi": fake_x402_http_middleware_fastapi,
            "x402.mechanisms.evm.exact": fake_x402_mechanisms_evm_exact,
            "agent": fake_agent,
            "clickhouse_client": fake_clickhouse,
            "monitor": fake_monitor,
        },
    ):
        with mock.patch.dict(os.environ, {"AGENT_WALLET_ADDRESS": "0xabc", "X402_PRICE_USDC": "50000"}, clear=False):
            sys.modules.pop("server", None)
            module = importlib.import_module("server")

    return module, captured


class ServerPaymentRoutesTest(unittest.TestCase):
    def test_analyze_stream_is_the_paid_route(self):
        module, captured = load_server_module()

        self.assertEqual(
            captured["routes"],
            {
                "POST /analyze-stream": {
                    "accepts": {
                        "scheme": "exact",
                        "payTo": "0xabc",
                        "price": "50000",
                        "network": "eip155:84532",
                    }
                }
            },
        )
        self.assertNotIn("POST /analyze-item", captured["routes"])
        self.assertIn("POST /analyze-stream", module._routes)

    def test_local_mock_wallet_bypasses_payment_middleware_for_stream(self):
        module, _captured = load_server_module()

        async def failing_x402(_request, _call_next):
            raise AssertionError("x402 middleware should be bypassed for local mock wallet requests")

        async def call_next(request):
            return {"path": request.url.path}

        module._x402 = failing_x402
        request = types.SimpleNamespace(
            method="POST",
            url=types.SimpleNamespace(path="/analyze-stream"),
            headers={module.MOCK_PAYMENT_BYPASS_HEADER: "true"},
            client=types.SimpleNamespace(host="127.0.0.1"),
        )

        self.assertEqual(asyncio.run(module.x402_middleware(request, call_next)), {"path": "/analyze-stream"})

    def test_remote_mock_wallet_header_still_uses_payment_middleware(self):
        module, _captured = load_server_module()

        async def paid_x402(_request, _call_next):
            return {"paid": True}

        async def call_next(_request):
            return {"paid": False}

        module._x402 = paid_x402
        request = types.SimpleNamespace(
            method="POST",
            url=types.SimpleNamespace(path="/analyze-stream"),
            headers={module.MOCK_PAYMENT_BYPASS_HEADER: "true"},
            client=types.SimpleNamespace(host="203.0.113.10"),
        )

        self.assertEqual(asyncio.run(module.x402_middleware(request, call_next)), {"paid": True})


if __name__ == "__main__":
    unittest.main()
