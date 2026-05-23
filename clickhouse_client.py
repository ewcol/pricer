"""ClickHouse data layer — connection, schema init, and CRUD."""
import os
import math
import clickhouse_connect
from dotenv import load_dotenv

load_dotenv()

_db = os.getenv("CLICKHOUSE_DATABASE", "ebay_agent")

# Connect without specifying the database so we can create it if needed
_bootstrap = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST"),
    port=int(os.getenv("CLICKHOUSE_PORT", "8443")),
    username=os.getenv("CLICKHOUSE_USER", "default"),
    password=os.getenv("CLICKHOUSE_PASSWORD"),
    secure=True,
)
_bootstrap.command(f"CREATE DATABASE IF NOT EXISTS {_db}")
_bootstrap.close()

client = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST"),
    port=int(os.getenv("CLICKHOUSE_PORT", "8443")),
    username=os.getenv("CLICKHOUSE_USER", "default"),
    password=os.getenv("CLICKHOUSE_PASSWORD"),
    database=_db,
    secure=True,
)

client.command("""
    CREATE TABLE IF NOT EXISTS tracked_items (
        item_id              String,
        title                String,
        recommended_price    Float32,
        currency             String DEFAULT 'USD',
        image_url            String DEFAULT '',
        listed_at            DateTime DEFAULT now(),
        notes                String,
        current_market_price Float32 DEFAULT 0,
        price_drift_pct      Float32 DEFAULT 0,
        last_checked_at      DateTime DEFAULT now()
    )
    ENGINE = MergeTree()
    ORDER BY listed_at
""")

client.command("ALTER TABLE tracked_items ADD COLUMN IF NOT EXISTS image_url String DEFAULT ''")

client.command("""
    CREATE TABLE IF NOT EXISTS price_history (
        item_id      String,
        old_price    Float32,
        new_price    Float32,
        drift_pct    Float32,
        detected_at  DateTime DEFAULT now(),
        action_taken Enum('flagged', 'stable')
    )
    ENGINE = MergeTree()
    ORDER BY detected_at
""")


def insert_item(
    item_id: str,
    title: str,
    recommended_price: float,
    currency: str = "USD",
    image_url: str = "",
    notes: str = "",
) -> None:
    client.insert(
        "tracked_items",
        [[item_id, title, recommended_price, currency, image_url, notes]],
        column_names=["item_id", "title", "recommended_price", "currency", "image_url", "notes"],
    )


def get_all_items() -> list[dict]:
    result = client.query("""
        SELECT item_id, title, recommended_price, listed_at,
               image_url,
               current_market_price, price_drift_pct, last_checked_at
        FROM tracked_items ORDER BY listed_at DESC
    """)
    return [
        {
            "item_id": row[0],
            "title": row[1],
            "recommended_price": row[2],
            "listed_at": str(row[3]),
            "image_url": row[4],
            "current_market_price": row[5],
            "price_drift_pct": row[6],
            "last_checked_at": str(row[7]),
        }
        for row in result.result_rows
    ]


def get_price_history(item_id: str) -> list[dict]:
    result = client.query(
        """
        SELECT old_price, new_price, drift_pct, detected_at, action_taken
        FROM price_history WHERE item_id = {id:String} ORDER BY detected_at ASC
        """,
        parameters={"id": item_id},
    )
    return [
        {
            "old_price": row[0],
            "new_price": row[1],
            "drift_pct": row[2],
            "detected_at": str(row[3]),
            "action_taken": row[4],
        }
        for row in result.result_rows
    ]


def get_portfolio_summary() -> dict:
    result = client.query("""
        SELECT
            count()                                          AS total,
            avgIf(price_drift_pct, current_market_price > 0) AS avg_drift,
            countIf(abs(price_drift_pct) >= 10)              AS flagged
        FROM tracked_items
    """)
    row = result.result_rows[0] if result.result_rows else (0, 0.0, 0)
    avg_drift = float(row[1]) if row[1] is not None else 0.0
    if not math.isfinite(avg_drift):
        avg_drift = 0.0
    return {
        "total": int(row[0]),
        "avg_drift": avg_drift,
        "flagged": int(row[2]),
    }


def update_item_market_price(item_id: str, current_price: float, drift_pct: float) -> None:
    client.command(
        "ALTER TABLE tracked_items UPDATE "
        "current_market_price = {price:Float32}, "
        "price_drift_pct = {drift:Float32}, "
        "last_checked_at = now() "
        "WHERE item_id = {id:String}",
        parameters={"price": current_price, "drift": drift_pct, "id": item_id},
    )


def log_price_history(
    item_id: str, old_price: float, new_price: float, drift_pct: float, action: str = "flagged"
) -> None:
    client.insert(
        "price_history",
        [[item_id, old_price, new_price, drift_pct, action]],
        column_names=["item_id", "old_price", "new_price", "drift_pct", "action_taken"],
    )


if __name__ == "__main__":
    print(get_all_items())
