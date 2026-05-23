"""ClickHouse data layer — connection, schema init, and CRUD."""
import os
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
        listed_at            DateTime DEFAULT now(),
        notes                String,
        current_market_price Float32 DEFAULT 0,
        price_drift_pct      Float32 DEFAULT 0,
        last_checked_at      DateTime DEFAULT now()
    )
    ENGINE = MergeTree()
    ORDER BY listed_at
""")

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
    notes: str = "",
) -> None:
    client.insert(
        "tracked_items",
        [[item_id, title, recommended_price, currency, notes]],
        column_names=["item_id", "title", "recommended_price", "currency", "notes"],
    )


def get_all_items() -> list[dict]:
    result = client.query("""
        SELECT item_id, title, recommended_price, listed_at,
               current_market_price, price_drift_pct, last_checked_at
        FROM tracked_items ORDER BY listed_at DESC
    """)
    return [
        {
            "item_id": row[0],
            "title": row[1],
            "recommended_price": row[2],
            "listed_at": str(row[3]),
            "current_market_price": row[4],
            "price_drift_pct": row[5],
            "last_checked_at": str(row[6]),
        }
        for row in result.result_rows
    ]


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
