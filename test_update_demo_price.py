import importlib
import os
import sys
import types
import unittest
from unittest import mock


class FakeResult:
    def __init__(self, rows):
        self.result_rows = rows


class FakeClient:
    def __init__(self):
        self.query_calls = []
        self.update_calls = []
        self.log_calls = []
        self.query_rows = []

    def query(self, sql, parameters=None):
        self.query_calls.append((sql, parameters))
        return FakeResult(self.query_rows)


def load_module(fake_client):
    fake_clickhouse_client = types.ModuleType("clickhouse_client")
    fake_clickhouse_client.client = fake_client
    fake_clickhouse_client.update_item_market_price = lambda *args, **kwargs: fake_client.update_calls.append(
        (args, kwargs)
    )
    fake_clickhouse_client.log_price_history = lambda *args, **kwargs: fake_client.log_calls.append(
        (args, kwargs)
    )

    with mock.patch.dict(
        sys.modules,
        {"clickhouse_client": fake_clickhouse_client},
    ):
        sys.modules.pop("update_demo_price", None)
        module = importlib.import_module("update_demo_price")

    return module


class UpdateDemoPriceTest(unittest.TestCase):
    def test_main_updates_and_logs_default_price(self):
        fake_client = FakeClient()
        fake_client.query_rows = [("item-123", "Test Item", 100.0, 80.0)]
        module = load_module(fake_client)

        exit_code = module.main(["item-123"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(fake_client.update_calls), 1)
        self.assertEqual(fake_client.update_calls[0][0], ("item-123", 120.0, 20.0))
        self.assertEqual(len(fake_client.log_calls), 1)
        self.assertEqual(fake_client.log_calls[0][0], ("item-123", 80.0, 120.0, 20.0, "flagged"))

    def test_main_returns_error_when_item_missing(self):
        fake_client = FakeClient()
        fake_client.query_rows = []
        module = load_module(fake_client)

        with mock.patch("sys.stderr", new=types.SimpleNamespace(write=lambda *args, **kwargs: None)):
            exit_code = module.main(["missing-item"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(fake_client.update_calls, [])
        self.assertEqual(fake_client.log_calls, [])


if __name__ == "__main__":
    unittest.main()
