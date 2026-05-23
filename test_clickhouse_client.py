import importlib
import os
import sys
import types
import unittest
from unittest import mock
from datetime import datetime


class FakeResult:
    def __init__(self, rows):
        self.result_rows = rows


class FakeClient:
    def __init__(self):
        self.command_calls = []
        self.query_calls = []
        self.insert_calls = []
        self.closed = False
        self.query_handler = None

    def command(self, sql, parameters=None):
        self.command_calls.append((sql, parameters))

    def close(self):
        self.closed = True

    def query(self, sql, parameters=None):
        self.query_calls.append((sql, parameters))
        if self.query_handler is None:
            return FakeResult([])
        return FakeResult(self.query_handler(sql, parameters))

    def insert(self, table, rows, column_names=None):
        self.insert_calls.append((table, rows, column_names))


def load_module():
    fake_client = FakeClient()
    fake_clickhouse = types.ModuleType("clickhouse_connect")
    fake_clickhouse.get_client = lambda **kwargs: fake_client
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None

    env = {
        "CLICKHOUSE_HOST": "localhost",
        "CLICKHOUSE_PORT": "8443",
        "CLICKHOUSE_USER": "default",
        "CLICKHOUSE_PASSWORD": "",
        "CLICKHOUSE_DATABASE": "ebay_agent",
    }

    with mock.patch.dict(
        sys.modules,
        {
            "clickhouse_connect": fake_clickhouse,
            "dotenv": fake_dotenv,
        },
    ):
        with mock.patch.dict(os.environ, env, clear=False):
            sys.modules.pop("clickhouse_client", None)
            module = importlib.import_module("clickhouse_client")

    return module, fake_client


class ClickHouseClientTest(unittest.TestCase):
    def test_insert_item_includes_image_url(self):
        module, fake_client = load_module()

        module.insert_item(
            item_id="item-123",
            title="Test Item",
            recommended_price=19.99,
            image_url="https://i.ibb.co/example.jpg",
            notes="note",
        )

        self.assertEqual(fake_client.insert_calls[-1][0], "tracked_items")
        self.assertEqual(
            fake_client.insert_calls[-1][2],
            ["item_id", "title", "recommended_price", "currency", "image_url", "notes"],
        )
        self.assertEqual(fake_client.insert_calls[-1][1][0][4], "https://i.ibb.co/example.jpg")

    def test_get_price_history_formats_rows(self):
        module, fake_client = load_module()
        fake_client.query_handler = lambda sql, params: [
            (10.0, 12.5, 25.0, datetime(2026, 1, 2, 3, 4, 5), "flagged"),
        ]

        result = module.get_price_history("item-123")

        self.assertEqual(
            result,
            [{
                "old_price": 10.0,
                "new_price": 12.5,
                "drift_pct": 25.0,
                "detected_at": "2026-01-02 03:04:05",
                "action_taken": "flagged",
            }],
        )
        self.assertIn("ORDER BY detected_at ASC", fake_client.query_calls[-1][0])
        self.assertEqual(fake_client.query_calls[-1][1], {"id": "item-123"})

    def test_get_portfolio_summary_normalizes_row(self):
        module, fake_client = load_module()
        fake_client.query_handler = lambda sql, params: [
            (7, 4.25, 2),
        ]

        result = module.get_portfolio_summary()

        self.assertEqual(result, {
            "total": 7,
            "avg_drift": 4.25,
            "flagged": 2,
        })
        self.assertIn("avgIf(price_drift_pct, current_market_price > 0)", fake_client.query_calls[-1][0])
        self.assertIn("countIf(abs(price_drift_pct) >= 10)", fake_client.query_calls[-1][0])


if __name__ == "__main__":
    unittest.main()
