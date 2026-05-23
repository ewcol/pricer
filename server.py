"""FastAPI entry point — x402-gated /analyze-stream + React SPA at /."""
import os
import json
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

from x402 import x402ResourceServer
from x402.http import HTTPFacilitatorClient
from x402.http.middleware.fastapi import payment_middleware
from x402.mechanisms.evm.exact import ExactEvmServerScheme

from agent import run_agent, run_agent_stream
from clickhouse_client import (
    insert_item,
    get_all_items,
    get_price_history,
    get_portfolio_summary,
)
from monitor import schedule_item_check, cancel_item_check

AGENT_WALLET = os.getenv("AGENT_WALLET_ADDRESS", "")
USDC_BASE = os.getenv("USDC_BASE_ADDRESS", "0x833589fcd6eA067d4b6f71A3d7e95e5F49c6Ef3")
X402_PRICE = int(os.getenv("X402_PRICE_USDC", "50000"))
MOCK_PAYMENT_BYPASS_HEADER = "x-pricer-mock-wallet"
LOCAL_CLIENT_HOSTS = {"127.0.0.1", "::1", "localhost"}

# Base Sepolia testnet — supported by x402.org/facilitator (mainnet requires self-hosted facilitator)
BASE_NETWORK = "eip155:84532"

# x402 server — uses Coinbase's public facilitator by default
_facilitator = HTTPFacilitatorClient()
_x402_server = x402ResourceServer(_facilitator)
_x402_server.register(BASE_NETWORK, ExactEvmServerScheme())

# Gate only POST /analyze-stream; the initial analysis is the paid action
_routes = {
    "POST /analyze-stream": {
        "accepts": {
            "scheme": "exact",
            "payTo": AGENT_WALLET,
            "price": str(X402_PRICE),
            "network": BASE_NETWORK,
        }
    }
}

_x402 = payment_middleware(routes=_routes, server=_x402_server)

app = FastAPI(title="eBay Seller Agent API")


def _is_paid_analyze_request(request: Request) -> bool:
    return request.method == "POST" and request.url.path == "/analyze-stream"


def _is_local_mock_payment_bypass(request: Request) -> bool:
    client_host = getattr(getattr(request, "client", None), "host", "")
    return (
        request.headers.get(MOCK_PAYMENT_BYPASS_HEADER) == "true"
        and client_host in LOCAL_CLIENT_HOSTS
    )


@app.middleware("http")
async def x402_middleware(request: Request, call_next):
    if _is_paid_analyze_request(request) and (not AGENT_WALLET or _is_local_mock_payment_bypass(request)):
        return await call_next(request)
    return await _x402(request, call_next)


class AnalyzeRequest(BaseModel):
    image_base64: str


class TrackRequest(BaseModel):
    item_id: str
    title: str
    recommended_price: float
    image_url: str = ""
    notes: str = ""


@app.post("/analyze-item")
async def analyze_item(req: AnalyzeRequest) -> dict:
    """Direct analysis endpoint for clients that don't need streaming."""
    return await run_agent(req.image_base64, include_image_url=True)


@app.post("/analyze-preview")
async def analyze_preview(req: AnalyzeRequest) -> dict:
    """Unprotected preview endpoint for demo use."""
    return await run_agent(req.image_base64, include_image_url=True)


@app.post("/analyze-stream")
async def analyze_stream(req: AnalyzeRequest):
    """SSE endpoint: streams step events then the final result."""
    async def event_generator():
        async for event in run_agent_stream(req.image_base64):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/tracked-items")
async def tracked_items() -> list[dict]:
    return get_all_items()


@app.get("/price-history/{item_id}")
async def price_history(item_id: str) -> list[dict]:
    return get_price_history(item_id)


@app.get("/portfolio-summary")
async def portfolio_summary() -> dict:
    return get_portfolio_summary()


@app.post("/track-item")
async def track_item(req: TrackRequest) -> dict:
    insert_item(
        item_id=req.item_id.strip(),
        title=req.title,
        recommended_price=req.recommended_price,
        image_url=req.image_url,
        notes=req.notes,
    )
    return {"status": "ok", "item_id": req.item_id.strip()}


class ItemIdRequest(BaseModel):
    item_id: str


@app.post("/schedule-check")
async def schedule_check(req: ItemIdRequest) -> dict:
    msg = schedule_item_check(req.item_id)
    return {"status": "ok", "message": msg}


@app.post("/cancel-check")
async def cancel_check(req: ItemIdRequest) -> dict:
    msg = cancel_item_check(req.item_id)
    return {"status": "ok", "message": msg}


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve React SPA from frontend/dist — fall through to index.html for client routing
_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        index = os.path.join(_dist, "index.html")
        return FileResponse(index)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
