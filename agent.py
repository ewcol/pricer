"""Multi-agent eBay listing pipeline: vision → reverse image search (parallel) → reconcile → price research → listing."""
import os
import json
import base64
import statistics
import asyncio
import io
import logging
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
from marketplace_sources import (
    MarketplaceSource,
    build_search_query,
    select_marketplace_sources,
)

load_dotenv()

_genai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
_nimble = Nimble(api_key=os.getenv("NIMBLE_API_KEY"))
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

async def identify_item(image_base64: str) -> dict:
    """Gemini vision identification — returns item info with a confidence score."""
    prompt = """
    Look at this item and return a JSON object with these exact keys:
    - item_name: string
    - brand: string (or "Unknown" if not visible)
    - condition_guess: string (e.g. "Good", "Fair", "Excellent")
    - search_keywords: list of 3-5 strings for eBay sold-listing searches
    - confidence: float between 0 and 1 (how certain you are about the identification)
    - reasoning: string (one sentence on why you are or aren't confident)
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


async def _upload_to_imgbb(image_base64: str) -> str:
    """Upload image to imgbb and return the public URL."""
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.imgbb.com/1/upload",
            data={"key": os.getenv("IMGBB_API_KEY"), "image": image_base64},
            timeout=30,
        )
        resp.raise_for_status()
        image_url = resp.json()["data"]["url"]
        logger.debug("imgbb image_url=%s", image_url)
        return image_url


async def reverse_image_search(image_base64: str) -> dict:
    """Upload image to imgbb, then run SerpApi Google Lens for visual matches."""
    import httpx
    image_url = await _upload_to_imgbb(image_base64)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_lens",
                "url": image_url,
                "api_key": os.getenv("SERPAPI_KEY"),
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    hits: list[dict] = []
    for match in data.get("visual_matches", [])[:8]:
        hits.append({
            "title": match.get("title", ""),
            "source": match.get("source", ""),
            "url": match.get("link", ""),
            "price": match.get("price", {}).get("value") if match.get("price") else None,
        })

    return {
        "image_url": image_url,
        "hits": hits,
    }


async def reconcile_identification(
    gemini_result: dict, reverse_search_result: dict
) -> dict:
    """Resolve identification by prioritizing reverse-image evidence over Gemini's guess."""
    prompt = f"""
    You are identifying an item for an eBay listing. You have two independent signals:

    1. GOOGLE LENS VISUAL MATCHES (primary source of truth for brand/model):
    {json.dumps(reverse_search_result.get("hits", []), indent=2)}

    2. GEMINI DIRECT IDENTIFICATION (secondary; may be wrong):
    {json.dumps(gemini_result, indent=2)}

    Use the Google Lens matches as the primary evidence for brand and model.
    If the Lens matches consistently point to a different brand than Gemini, prefer the Lens brand.
    Only fall back to Gemini when the Lens results are sparse, inconsistent, or clearly unrelated.
    If the signals disagree, set signals_agree to false and lower confidence.

    Return a JSON object with these exact keys:
    - item_name: string (best identification)
    - brand: string (or "Unknown")
    - condition_guess: string
    - search_keywords: list of 3-5 strings optimized for eBay sold-listing searches
    - confidence: float 0-1
    - signals_agree: boolean
    - reasoning: string (one sentence explaining the reconciliation)
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


async def _research_source_prices(source: MarketplaceSource, query: str) -> dict:
    try:
        resp = await asyncio.to_thread(
            _nimble.agent.run,
            agent=source.agent_name,
            params={source.param_name: query},
        )
    except Exception as exc:
        return {
            "source": source.key,
            "label": source.label,
            "prices_found": [],
            "source_urls": [],
            "note": f"{source.label} search failed: {exc}",
        }

    listings = resp.data.parsing if resp.data and resp.data.parsing else []
    if not isinstance(listings, list):
        listings = []

    prices: list[float] = []
    source_urls: list[str] = []

    for item in listings:
        url = getattr(item, "url", None) or ""
        if url:
            source_urls.append(url)
        raw_price = getattr(item, "price", None)
        if raw_price is not None:
            try:
                price = float(raw_price)
                if price > 0:
                    prices.append(price)
            except (ValueError, TypeError):
                pass

    note = ""
    if not prices:
        note = f"No {source.label} listings with prices found."

    return {
        "source": source.key,
        "label": source.label,
        "prices_found": prices,
        "source_urls": source_urls[:5],
        "note": note,
    }


async def research_prices(search_keywords: list[str], item_info: dict | None = None) -> dict:
    query = build_search_query(search_keywords)
    sources = select_marketplace_sources(item_info or search_keywords)

    source_results = await asyncio.gather(
        *[_research_source_prices(source, query) for source in sources]
    )

    raw_prices: list[float] = []
    weighted_prices: list[float] = []
    source_urls: list[str] = []
    source_breakdown: list[dict] = []

    for source, result in zip(sources, source_results):
        prices = result.get("prices_found", [])
        if prices:
            raw_prices.extend(prices)
            weighted_prices.extend(prices * max(1, source.priority))
        source_urls.extend(result.get("source_urls", []))
        source_breakdown.append(
            {
                "source": source.key,
                "label": source.label,
                "count": len(prices),
                "priority": source.priority,
                "note": result.get("note", ""),
            }
        )

    if not raw_prices:
        return {
            "prices_found": [],
            "weighted_prices": [],
            "low": None,
            "high": None,
            "recommended": None,
            "source_urls": source_urls[:10],
            "sources_used": [source.key for source in sources],
            "source_breakdown": source_breakdown,
            "note": "No marketplace listings with prices found. Recommend manual check.",
        }

    prices_for_median = weighted_prices or raw_prices
    median = statistics.median(prices_for_median)
    recommended = round(median - 0.01) + 0.99

    return {
        "prices_found": raw_prices,
        "weighted_prices": weighted_prices,
        "low": min(raw_prices),
        "high": max(raw_prices),
        "recommended": recommended,
        "source_urls": source_urls[:10],
        "sources_used": [source.key for source in sources],
        "source_breakdown": source_breakdown,
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
    Call research_prices with the provided search keywords to find secondary marketplace comps.
    Return only the JSON dict from research_prices — no prose.
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


async def run_agent_stream(image_base64: str):
    """Yield SSE-style step events, then the final result."""
    image_base64 = _resize_image_b64(image_base64)

    yield {"step": "vision", "status": "running", "label": "Identifying item via Gemini vision"}
    yield {"step": "image_search", "status": "running", "label": "Running reverse image search"}

    gemini_result, reverse_result = await asyncio.gather(
        identify_item(image_base64),
        reverse_image_search(image_base64),
    )
    yield {"step": "vision", "status": "done", "label": "Item identified", "data": {
        "item_name": gemini_result.get("item_name"),
        "brand": gemini_result.get("brand"),
    }}
    yield {"step": "image_search", "status": "done", "label": "Image search complete", "data": {
        "hits": len(reverse_result.get("hits", [])),
        "image_url": reverse_result.get("image_url"),
    }}

    yield {"step": "reconcile", "status": "running", "label": "Cross-referencing signals"}
    item_info = await reconcile_identification(gemini_result, reverse_result)
    yield {"step": "reconcile", "status": "done", "label": "Signals reconciled", "data": {
        "item_name": item_info.get("item_name"),
        "confidence": item_info.get("confidence"),
        "signals_agree": item_info.get("signals_agree"),
    }}

    yield {"step": "prices", "status": "running", "label": "Researching marketplace comps"}
    keywords = item_info.get("search_keywords", [])
    price_data = await research_prices(keywords, item_info)
    yield {"step": "prices", "status": "done", "label": f"Found {len(price_data.get('prices_found', []))} comp listings", "data": {
        "low": price_data.get("low"),
        "high": price_data.get("high"),
        "recommended": price_data.get("recommended"),
        "sources_used": price_data.get("sources_used", []),
    }}

    yield {"step": "listing", "status": "running", "label": "Generating eBay listing"}
    listing = await generate_listing(item_info, price_data)
    listing["item_name"] = item_info.get("item_name", "")
    listing["brand"] = item_info.get("brand", "")
    listing["condition_guess"] = item_info.get("condition_guess", "")
    listing["confidence"] = item_info.get("confidence")
    listing["signals_agree"] = item_info.get("signals_agree")
    listing["identification_reasoning"] = item_info.get("reasoning", "")
    listing["image_url"] = reverse_result.get("image_url", "")
    listing["search_keywords"] = item_info.get("search_keywords", [])
    listing["sources_used"] = price_data.get("sources_used", [])
    listing["source_breakdown"] = price_data.get("source_breakdown", [])
    listing["low"] = price_data.get("low")
    listing["high"] = price_data.get("high")
    yield {"step": "listing", "status": "done", "label": "Listing generated"}

    yield {"step": "result", "status": "done", "data": listing}


async def run_agent(image_base64: str, include_image_url: bool = False) -> dict:
    image_base64 = _resize_image_b64(image_base64)

    # Step 1: identify via Gemini vision + reverse image search in parallel
    gemini_result, reverse_result = await asyncio.gather(
        identify_item(image_base64),
        reverse_image_search(image_base64),
    )

    # Step 2: reconcile — cross-reference both signals for a high-confidence ID
    item_info = await reconcile_identification(gemini_result, reverse_result)

    # Step 3: marketplace price research using reconciled keywords
    keywords = item_info.get("search_keywords", [])
    price_data = await research_prices(keywords, item_info)

    # Step 4: generate listing
    listing = await generate_listing(item_info, price_data)

    listing["item_name"] = item_info.get("item_name", "")
    listing["brand"] = item_info.get("brand", "")
    listing["condition_guess"] = item_info.get("condition_guess", "")
    listing["confidence"] = item_info.get("confidence")
    listing["signals_agree"] = item_info.get("signals_agree")
    listing["identification_reasoning"] = item_info.get("reasoning", "")
    if include_image_url:
        listing["image_url"] = reverse_result.get("image_url", "")
    listing["search_keywords"] = item_info.get("search_keywords", [])
    listing["sources_used"] = price_data.get("sources_used", [])
    listing["source_breakdown"] = price_data.get("source_breakdown", [])
    listing["low"] = price_data.get("low")
    listing["high"] = price_data.get("high")

    return listing
