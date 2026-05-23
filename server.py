"""FastAPI entry point — x402-gated /analyze-item + Gradio UI mounted at /."""
import os
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import gradio as gr
from x402 import x402ResourceServer
from x402.http import HTTPFacilitatorClient
from x402.http.middleware.fastapi import payment_middleware
from x402.mechanisms.evm.exact import ExactEvmServerScheme

from agent import run_agent
from app import demo

AGENT_WALLET = os.getenv("AGENT_WALLET_ADDRESS", "")
USDC_BASE = os.getenv("USDC_BASE_ADDRESS", "0x833589fcd6eA067d4b6f71A3d7e95e5F49c6Ef3")
X402_PRICE = int(os.getenv("X402_PRICE_USDC", "50000"))

# Base Sepolia testnet — supported by x402.org/facilitator (mainnet requires self-hosted facilitator)
BASE_NETWORK = "eip155:84532"

# x402 server — uses Coinbase's public facilitator by default
_facilitator = HTTPFacilitatorClient()
_x402_server = x402ResourceServer(_facilitator)
_x402_server.register(BASE_NETWORK, ExactEvmServerScheme())

# Gate only POST /analyze-item; Gradio at / is free
_routes = {
    "POST /analyze-item": {
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


@app.middleware("http")
async def x402_middleware(request: Request, call_next):
    return await _x402(request, call_next)


class AnalyzeRequest(BaseModel):
    image_base64: str


@app.post("/analyze-item")
async def analyze_item(req: AnalyzeRequest) -> dict:
    """
    Pay-per-call endpoint: returns a full eBay listing from an item image.
    Requires x402 USDC payment on Base mainnet ($0.05 per call).
    Without payment: returns HTTP 402 with payment-required header.
    """
    return await run_agent(req.image_base64)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Mount Gradio UI at root — no payment required
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
