"""Gradio UI — Tab 1: analyze & list, Tab 2: tracked items + autonomy monitor."""
import os
import asyncio
import base64
import re
import threading
from PIL import Image
import io
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from agent import run_agent, research_prices
from clickhouse_client import insert_item, get_all_items, update_item_market_price, log_price_history


# ---------------------------------------------------------------------------
# Tab 1 state
# ---------------------------------------------------------------------------

_current_listing: dict = {}


def analyze_image(image_path):
    global _current_listing
    if image_path is None:
        return "Upload an image first.", "", "", "", "", ""

    with Image.open(image_path) as img:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG")
        image_b64 = base64.b64encode(buf.getvalue()).decode()

    listing = asyncio.run(run_agent(image_b64))
    _current_listing = listing

    if "error" in listing:
        return listing["error"], "", "", "", "", ""

    price_range = f"${listing.get('low', '?')} – ${listing.get('high', '?')}"
    recommended = f"${listing.get('recommended_price', '?')}"

    return (
        f"{listing.get('item_name', '')} — {listing.get('brand', '')} ({listing.get('condition_guess', '')})",
        price_range,
        recommended,
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category_suggestion", ""),
    )


def track_item(item_id: str):
    if not item_id.strip():
        return "Enter an eBay Item ID first."
    if not _current_listing:
        return "Analyze an item first."

    insert_item(
        item_id=item_id.strip(),
        title=_current_listing.get("title", ""),
        recommended_price=float(_current_listing.get("recommended_price", 0)),
        notes=_current_listing.get("price_rationale", ""),
    )
    return f"Tracked item {item_id}."


# ---------------------------------------------------------------------------
# Tab 2 — autonomy monitor
# ---------------------------------------------------------------------------

_stop_event = threading.Event()
_monitor_thread: threading.Thread | None = None


def _extract_keywords(title: str) -> list[str]:
    stop = {"the", "a", "an", "and", "or", "for", "with", "used", "like", "new", "great"}
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    return [w for w in words if w not in stop][:5]


async def _check_prices_once():
    items = get_all_items()
    for item in items:
        keywords = _extract_keywords(item["title"])
        if not keywords:
            continue
        try:
            market = await research_prices(keywords)
            current = market.get("recommended")
            if current:
                listed = item["recommended_price"]
                drift = (current - listed) / listed * 100
                update_item_market_price(item["item_id"], current, drift)
                if abs(drift) >= 10:
                    log_price_history(item["item_id"], listed, current, drift, "flagged")
        except Exception:
            pass


async def _monitor_loop():
    while not _stop_event.is_set():
        await _check_prices_once()
        await asyncio.sleep(30)


def start_monitor():
    global _monitor_thread
    _stop_event.clear()
    if _monitor_thread is None or not _monitor_thread.is_alive():
        _monitor_thread = threading.Thread(
            target=lambda: asyncio.run(_monitor_loop()), daemon=True
        )
        _monitor_thread.start()
    return "Monitoring every 30s..."


def stop_monitor():
    _stop_event.set()
    return "Stopped."


def load_items():
    rows = get_all_items()
    result = []
    for r in rows:
        drift = r["price_drift_pct"]
        if drift <= -10:
            drift_label = f"⚠️ {drift:.1f}%"
        elif drift >= 10:
            drift_label = f"📈 +{drift:.1f}%"
        elif drift != 0:
            drift_label = f"{drift:+.1f}%"
        else:
            drift_label = "—"
        result.append([
            r["item_id"],
            r["title"],
            r["recommended_price"],
            r["current_market_price"] or "—",
            drift_label,
            r["listed_at"],
        ])
    return result


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def _seed_if_empty():
    rows = get_all_items()
    if len(rows) == 0:
        seed_items = [
            {
                "item_id": "186123456789",
                "title": "Apple iPhone 12 64GB Black Unlocked - Good Condition",
                "recommended_price": 219.99,
                "currency": "USD",
                "notes": "Median of 8 sold comps on eBay, range $180–$260",
            },
            {
                "item_id": "186987654321",
                "title": "Nintendo Switch Lite Yellow - Very Good Condition",
                "recommended_price": 159.99,
                "currency": "USD",
                "notes": "Median of 6 sold comps, range $140–$185",
            },
            {
                "item_id": "186555000111",
                "title": "Sony WH-1000XM4 Wireless Headphones Black - Good",
                "recommended_price": 189.99,
                "currency": "USD",
                "notes": "Median of 5 sold comps, range $160–$220",
            },
        ]
        for item in seed_items:
            insert_item(
                item_id=item["item_id"],
                title=item["title"],
                recommended_price=item["recommended_price"],
                currency=item["currency"],
                notes=item["notes"],
            )


_seed_if_empty()


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="eBay Seller Agent") as demo:
    with gr.Tab("Price & List"):
        with gr.Row():
            image_input = gr.Image(type="filepath", label="Upload Item Photo")
            analyze_btn = gr.Button("Analyze Item", variant="primary")

        item_summary = gr.Textbox(label="Identified Item", interactive=False)
        price_range_out = gr.Textbox(label="Price Range Found", interactive=False)
        recommended_out = gr.Textbox(label="Recommended Price", interactive=False, elem_id="recommended")

        listing_title = gr.Textbox(label="Suggested eBay Title", interactive=True)
        listing_desc = gr.Textbox(label="Description", lines=4, interactive=True)
        category_out = gr.Textbox(label="Category Suggestion", interactive=False)

        gr.Markdown("---\n### Got your listing live?")
        item_id_input = gr.Textbox(label="eBay Item ID", placeholder="e.g. 123456789012")
        track_btn = gr.Button("Track This Item")
        track_status = gr.Textbox(label="Status", interactive=False)

        analyze_btn.click(
            fn=analyze_image,
            inputs=[image_input],
            outputs=[item_summary, price_range_out, recommended_out, listing_title, listing_desc, category_out],
        )
        track_btn.click(
            fn=track_item,
            inputs=[item_id_input],
            outputs=[track_status],
        )

    with gr.Tab("Tracked Items"):
        with gr.Row():
            refresh_btn = gr.Button("Refresh")
            monitor_btn = gr.Button("Start Auto-Monitor", variant="secondary")
            stop_btn = gr.Button("Stop")
            monitor_status = gr.Textbox(label="Monitor Status", interactive=False, value="Stopped", scale=2)

        items_table = gr.Dataframe(
            headers=["Item ID", "Title", "Listed Price", "Market Price", "Drift", "Listed At"],
            datatype=["str", "str", "number", "str", "str", "str"],
            interactive=False,
        )

        refresh_btn.click(fn=load_items, inputs=[], outputs=[items_table])
        monitor_btn.click(fn=start_monitor, inputs=[], outputs=[monitor_status])
        stop_btn.click(fn=stop_monitor, inputs=[], outputs=[monitor_status])

        demo.load(fn=load_items, inputs=[], outputs=[items_table])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
