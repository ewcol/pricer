"""Multi-agent eBay listing pipeline: vision → price research (parallel) → listing."""
import os
import json
import base64
import statistics
import asyncio
import io
from nimble_python import Nimble
from PIL import Image
from google import genai
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import AgentTool
from google.genai import types as genai_types
from dotenv import load_dotenv

load_dotenv()

_genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
_nimble = Nimble(api_key=os.getenv("NIMBLE_API_KEY"))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

async def identify_item(image_base64: str) -> dict:
    prompt = """
    Look at this item and return a JSON object with these exact keys:
    - item_name: string
    - brand: string (or "Unknown" if not visible)
    - condition_guess: string (e.g. "Good", "Fair", "Excellent")
    - search_keywords: list of 3-5 strings for eBay sold-listing searches
    Return only the JSON object, no prose.
    """
    response = _genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=base64.b64decode(image_base64), mime_type="image/jpeg"),
            prompt,
        ],
    )
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


async def research_prices(search_keywords: list[str]) -> dict:
    query = " ".join(search_keywords)

    resp = await asyncio.to_thread(
        _nimble.agent.run,
        agent="ebay_search_2026_02_23_pbgj8oft",
        inputs={"keyword": query},
    )

    listings = resp.data.parsing if resp.data and resp.data.parsing else []
    if hasattr(listings, "model_dump"):
        listings = listings.model_dump()
    if not isinstance(listings, list):
        listings = []

    prices: list[float] = []
    source_urls: list[str] = []

    for item in listings:
        url = item.get("url") or item.get("link", "")
        if url:
            source_urls.append(url)
        raw_price = item.get("price") or item.get("buy_it_now_price") or item.get("current_price")
        if raw_price is not None:
            try:
                price = float(str(raw_price).replace("$", "").replace(",", "").strip())
                if price > 0:
                    prices.append(price)
            except ValueError:
                pass

    if not prices:
        return {
            "prices_found": [],
            "low": None,
            "high": None,
            "recommended": None,
            "source_urls": source_urls[:5],
            "note": "No eBay listings with prices found. Recommend manual eBay check.",
        }

    median = statistics.median(prices)
    recommended = round(median - 0.01) + 0.99

    return {
        "prices_found": prices,
        "low": min(prices),
        "high": max(prices),
        "recommended": recommended,
        "source_urls": source_urls[:5],
    }


async def generate_listing(item_info: dict, price_data: dict) -> dict:
    prompt = f"""
    You are an expert eBay seller. Based on the item info and price data below, generate a complete eBay listing.

    Item info: {json.dumps(item_info)}
    Price data: {json.dumps(price_data)}

    Return a JSON object with exactly these keys:
    - title: string, max 80 chars, eBay-style (Brand + Item + Key Spec + Condition)
    - description: string, 3-4 sentences, factual, no fluff
    - category_suggestion: string, plain English (e.g. "Cell Phones & Smartphones")
    - recommended_price: number (use price_data["recommended"] if available, else estimate)
    - price_rationale: string, one sentence explaining the price based on comps

    Return only the JSON object, no prose.
    """
    response = _genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
    )
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


# ---------------------------------------------------------------------------
# Sub-agents
# ---------------------------------------------------------------------------

vision_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="vision_agent",
    instruction="""
    Analyze the provided item image (base64) and call identify_item.
    Return only the JSON dict from identify_item — no prose.
    """,
    tools=[identify_item],
)

price_agent_ebay = LlmAgent(
    model="gemini-2.5-flash",
    name="price_agent_ebay",
    instruction="""
    Call research_prices with the provided search keywords to find eBay sold listing prices.
    Return only the JSON dict from research_prices — no prose.
    """,
    tools=[research_prices],
)

price_agent_web = LlmAgent(
    model="gemini-2.5-flash",
    name="price_agent_web",
    instruction="""
    Call research_prices with the provided search keywords appended with 'price used' to find
    general web pricing data. Return only the JSON dict from research_prices — no prose.
    """,
    tools=[research_prices],
)

listing_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="listing_agent",
    instruction="""
    Call generate_listing with the provided item_info and price_data.
    Return only the JSON dict from generate_listing — no prose.
    """,
    tools=[generate_listing],
)

# ---------------------------------------------------------------------------
# Root orchestrator
# ---------------------------------------------------------------------------

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="ebay_orchestrator",
    instruction="""
    You are an eBay listing orchestrator. You receive item_info JSON (with search_keywords).

    Step 1: Call price_agent_ebay and price_agent_web in parallel using the search_keywords.
            Merge their price results: combine prices_found lists,
            recalculate low/high/recommended as the median of all combined prices.

    Step 2: Call listing_agent with item_info and the merged price_data.

    Return only the final listing JSON from listing_agent. No prose.
    """,
    tools=[
        AgentTool(agent=price_agent_ebay),
        AgentTool(agent=price_agent_web),
        AgentTool(agent=listing_agent),
    ],
)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name="ebay_agent", session_service=_session_service)


def _resize_image_b64(image_base64: str, max_px: int = 1024) -> str:
    raw = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if max(img.size) > max_px:
        img.thumbnail((max_px, max_px), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


async def run_agent(image_base64: str) -> dict:
    image_base64 = _resize_image_b64(image_base64)

    # Step 1: vision
    item_info = await identify_item(image_base64)

    # Step 2: parallel price research from eBay and web
    keywords = item_info.get("search_keywords", [])
    web_keywords = keywords + ["price used"]
    ebay_result, web_result = await asyncio.gather(
        research_prices(keywords),
        research_prices(web_keywords),
    )

    all_prices = ebay_result.get("prices_found", []) + web_result.get("prices_found", [])
    if all_prices:
        median = statistics.median(all_prices)
        recommended = round(median - 0.01) + 0.99
        price_data = {
            "prices_found": all_prices,
            "low": min(all_prices),
            "high": max(all_prices),
            "recommended": recommended,
            "source_urls": (ebay_result.get("source_urls", []) + web_result.get("source_urls", []))[:5],
        }
    else:
        price_data = ebay_result  # fallback with note

    # Step 3: generate listing
    listing = await generate_listing(item_info, price_data)

    listing["item_name"] = item_info.get("item_name", "")
    listing["brand"] = item_info.get("brand", "")
    listing["condition_guess"] = item_info.get("condition_guess", "")
    listing["low"] = price_data.get("low")
    listing["high"] = price_data.get("high")

    return listing
