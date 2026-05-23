import importlib
import sys
import types
import unittest
from unittest import mock


class _FakeTimer:
    instances = []

    def __init__(self, delay, callback):
        self.delay = delay
        self.callback = callback
        self.daemon = False
        self.started = False
        self.canceled = False
        self.__class__.instances.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.canceled = True


def load_monitor_module():
    fake_clickhouse = types.ModuleType("clickhouse_client")
    fake_clickhouse.get_all_items = lambda: []
    fake_clickhouse.update_item_market_price = lambda *args, **kwargs: None
    fake_clickhouse.log_price_history = lambda *args, **kwargs: None

    fake_agent = types.ModuleType("agent")
    fake_agent.research_prices = lambda *args, **kwargs: None

    with mock.patch.dict(sys.modules, {"clickhouse_client": fake_clickhouse, "agent": fake_agent}):
        sys.modules.pop("monitor", None)
        return importlib.import_module("monitor")


class MonitorScheduleTest(unittest.TestCase):
    def test_schedule_uses_five_second_delay(self):
        module = load_monitor_module()
        _FakeTimer.instances.clear()

        with mock.patch.object(module.threading, "Timer", _FakeTimer):
            message = module.schedule_item_check("  ebay-123  ")

        self.assertEqual(message, "Check scheduled for ebay-123 in 5 seconds.")
        self.assertEqual(len(_FakeTimer.instances), 1)
        self.assertEqual(_FakeTimer.instances[0].delay, 5.0)
        self.assertTrue(_FakeTimer.instances[0].started)
        self.assertTrue(_FakeTimer.instances[0].daemon)


if __name__ == "__main__":
    unittest.main()
