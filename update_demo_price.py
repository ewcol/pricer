#!/usr/bin/env python3
"""Update a tracked item's market price and log a price-history event."""
from __future__ import annotations

import argparse
import sys
from typing import Any

from clickhouse_client import client, log_price_history, update_item_market_price


def _fetch_tracked_item(item_id: str) -> dict[str, Any] | None:
    result = client.query(
        """
        SELECT item_id, title, recommended_price, current_market_price
        FROM tracked_items
        WHERE item_id = {id:String}
        LIMIT 1
        """,
        parameters={"id": item_id},
    )
    if not result.result_rows:
        return None

    row = result.result_rows[0]
    return {
        "item_id": row[0],
        "title": row[1],
        "recommended_price": float(row[2]),
        "current_market_price": float(row[3]),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Update a tracked item price for demoing the tracking UI."
    )
    parser.add_argument("item_id", help="Tracked item_id to update")
    parser.add_argument(
        "--price",
        type=float,
        help="New market price. If omitted, the script bumps the recommended price by 20 percent.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    item = _fetch_tracked_item(args.item_id)
    if item is None:
        print(f"item not found: {args.item_id}", file=sys.stderr)
        return 1

    recommended_price = item["recommended_price"]
    if recommended_price <= 0:
        print(f"item has invalid recommended_price: {recommended_price}", file=sys.stderr)
        return 1

    current_price = item["current_market_price"] or recommended_price
    new_price = args.price if args.price is not None else round(recommended_price * 1.2, 2)
    drift_pct = ((new_price - recommended_price) / recommended_price) * 100.0
    action = "flagged" if abs(drift_pct) >= 10 else "stable"

    update_item_market_price(args.item_id, new_price, drift_pct)
    log_price_history(args.item_id, current_price, new_price, drift_pct, action)

    print(
        f"updated {args.item_id}: ${current_price:.2f} -> ${new_price:.2f} "
        f"({drift_pct:+.1f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
