"""Gradio UI — Tab 1: analyze & list, Tab 2: tracked items + per-item monitor."""
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
        return "Upload an image first.", "", "", "", "", "", ""

    with Image.open(image_path) as img:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG")
        image_b64 = base64.b64encode(buf.getvalue()).decode()

    listing = asyncio.run(run_agent(image_b64, include_image_url=True))
    _current_listing = listing

    if "error" in listing:
        return listing["error"], "", "", "", "", "", ""

    price_range = f"${listing.get('low', '?')} – ${listing.get('high', '?')}"
    recommended = f"${listing.get('recommended_price', '?')}"

    confidence = listing.get("confidence")
    signals_agree = listing.get("signals_agree")
    reasoning = listing.get("identification_reasoning", "")
    image_url = listing.get("image_url", "")
    if confidence is not None:
        agree_str = "✓ signals agree" if signals_agree else "⚠ signals disagree"
        confidence_str = f"{int(confidence * 100)}% confidence — {agree_str}\n{reasoning}"
    else:
        confidence_str = reasoning

    return (
        f"{listing.get('item_name', '')} — {listing.get('brand', '')} ({listing.get('condition_guess', '')})",
        confidence_str,
        price_range,
        recommended,
        image_url,
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
    scheduled = _schedule_item_check(item_id.strip())
    return f"Tracked item {item_id}. {scheduled}"


# ---------------------------------------------------------------------------
# Tab 2 — autonomy monitor
# ---------------------------------------------------------------------------

_pending_checks: dict[str, threading.Timer] = {}
_pending_checks_lock = threading.Lock()
_selected_item_id = ""


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


async def _check_single_item_once(item_id: str):
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


def _schedule_item_check(item_id: str) -> str:
    item_id = item_id.strip()
    if not item_id:
        return "Select an item first."

    def _run_check():
        try:
            asyncio.run(_check_single_item_once(item_id))
        finally:
            with _pending_checks_lock:
                _pending_checks.pop(item_id, None)

    with _pending_checks_lock:
        existing = _pending_checks.get(item_id)
        if existing is not None:
            existing.cancel()
        timer = threading.Timer(30.0, _run_check)
        timer.daemon = True
        _pending_checks[item_id] = timer
        timer.start()

    return f"Scheduled one check for {item_id} in 30 seconds."


def _cancel_item_check(item_id: str) -> str:
    item_id = item_id.strip()
    if not item_id:
        return "Select an item first."

    with _pending_checks_lock:
        timer = _pending_checks.pop(item_id, None)
        if timer is None:
            return f"No pending check for {item_id}."
        timer.cancel()

    return f"Canceled pending check for {item_id}."


def select_tracked_item(evt: gr.SelectData):
    global _selected_item_id

    if not evt.selected or not evt.row_value:
        _selected_item_id = ""
        return "", "No item selected."

    item_id = str(evt.row_value[0])
    title = str(evt.row_value[1]) if len(evt.row_value) > 1 else ""
    _selected_item_id = item_id
    return item_id, f"Selected {item_id}: {title}"


def schedule_selected_monitor(item_id: str):
    return _schedule_item_check(item_id)


def cancel_selected_monitor(item_id: str):
    return _cancel_item_check(item_id)


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
        confidence_out = gr.Textbox(label="Identification Confidence", interactive=False)
        price_range_out = gr.Textbox(label="Price Range Found", interactive=False)
        recommended_out = gr.Textbox(label="Recommended Price", interactive=False, elem_id="recommended")
        image_url_out = gr.Textbox(label="Published Image URL", interactive=False)

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
            outputs=[
                item_summary,
                confidence_out,
                price_range_out,
                recommended_out,
                image_url_out,
                listing_title,
                listing_desc,
                category_out,
            ],
        )
        track_btn.click(
            fn=track_item,
            inputs=[item_id_input],
            outputs=[track_status],
        )

    with gr.Tab("Tracked Items"):
        with gr.Row():
            refresh_btn = gr.Button("Refresh")
            monitor_status = gr.Textbox(label="Monitor Status", interactive=False, value="Select a row to monitor", scale=2)

        items_table = gr.Dataframe(
            headers=["Item ID", "Title", "Listed Price", "Market Price", "Drift", "Listed At"],
            datatype=["str", "str", "number", "str", "str", "str"],
            interactive=False,
        )

        selected_item_id = gr.Textbox(label="Selected Item ID", interactive=False)
        with gr.Row():
            schedule_btn = gr.Button("Schedule 30s Check", variant="secondary")
            cancel_btn = gr.Button("Cancel Pending Check")

        refresh_btn.click(fn=load_items, inputs=[], outputs=[items_table])
        items_table.select(
            fn=select_tracked_item,
            inputs=[],
            outputs=[selected_item_id, monitor_status],
        )
        schedule_btn.click(
            fn=schedule_selected_monitor,
            inputs=[selected_item_id],
            outputs=[monitor_status],
        )
        cancel_btn.click(
            fn=cancel_selected_monitor,
            inputs=[selected_item_id],
            outputs=[monitor_status],
        )

        demo.load(fn=load_items, inputs=[], outputs=[items_table])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
