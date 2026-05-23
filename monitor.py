"""Background price-check scheduler — no Gradio dependency."""
import asyncio
import re
import threading

from clickhouse_client import get_all_items, update_item_market_price, log_price_history
from agent import research_prices

_pending: dict[str, threading.Timer] = {}
_lock = threading.Lock()


def _extract_keywords(title: str) -> list[str]:
    stop = {"the", "a", "an", "and", "or", "for", "with", "used", "like", "new", "great"}
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    return [w for w in words if w not in stop][:5]


async def _check_item(item_id: str) -> None:
    items = {item["item_id"]: item for item in get_all_items()}
    item = items.get(item_id)
    if item is None:
        return
    keywords = _extract_keywords(item["title"])
    if not keywords:
        return
    try:
        market = await research_prices(keywords)
        current = market.get("recommended")
        if current:
            listed = item["recommended_price"]
            drift = (current - listed) / listed * 100
            update_item_market_price(item_id, current, drift)
            if abs(drift) >= 10:
                log_price_history(item_id, listed, current, drift, "flagged")
    except Exception:
        pass


def schedule_item_check(item_id: str) -> str:
    item_id = item_id.strip()
    if not item_id:
        return "No item ID provided."

    def _run():
        try:
            asyncio.run(_check_item(item_id))
        finally:
            with _lock:
                _pending.pop(item_id, None)

    with _lock:
        existing = _pending.pop(item_id, None)
        if existing:
            existing.cancel()
        t = threading.Timer(30.0, _run)
        t.daemon = True
        _pending[item_id] = t
        t.start()

    return f"Check scheduled for {item_id} in 30 seconds."


def cancel_item_check(item_id: str) -> str:
    item_id = item_id.strip()
    if not item_id:
        return "No item ID provided."
    with _lock:
        t = _pending.pop(item_id, None)
        if t is None:
            return f"No pending check for {item_id}."
        t.cancel()
    return f"Canceled check for {item_id}."
