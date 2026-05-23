# Monetization Plan

## Current State

- `server.py` already has x402 middleware, but only `POST /analyze-item` is gated.
- The shipped frontend currently calls `/analyze-stream`, so the visible demo flow bypasses the paid route.
- The app has no entitlement, credit, or subscription model yet.
- The project already depends on `x402`, `fastapi`, `uvicorn`, and `clickhouse`, so the core payment plumbing is mostly in place.

## Recommended Rail Split

Use one rail per job:

- x402 for the core agent-facing API
- MPP for any Stripe-backed human purchase / top-up flow
- CDP for wallet infrastructure and x402 wallet setup
- agentic.market for discovery and distribution of the paid API

## Why This Split

- x402 is the cleanest fit for the current product because the app already exposes HTTP endpoints and the codebase already includes x402 middleware.
- MPP is not a second implementation of the same endpoint; it is the better fit if we want a Stripe-native purchase path for humans or an agent wallet that can spend through Stripe rails.
- CDP is the right infrastructure layer for programmatic wallets and x402 seller wallet management.
- agentic.market is the discovery layer, not the billing system; it is how agents find and invoke the paid endpoint.

## Implementation Path

1. Make the paid path visible in the demo by routing the main analyze action through the x402-gated endpoint.
2. Add a lightweight usage/entitlement record so we can distinguish free preview, paid analysis, and tracked monitoring.
3. Gate recurring monitoring separately from one-shot analysis.
4. Add a small balance or credits indicator in the frontend header or analysis panel.
5. Publish the endpoint metadata so it can be validated and listed on agentic.market.
6. If we want fiat/card access, add a Stripe/MPP purchase path as a separate top-up or subscription entrypoint.

## Proposed Product Shape

- Free preview: one low-friction, ungated preview endpoint or sample analysis.
- Paid analysis: one x402-protected analysis call per item.
- Paid monitoring: recurring x402 or MPP-backed checks for tracked items.
- Discovery: list the paid service on agentic.market so agents can find it directly.

## Questions To Confirm

- Do you want the primary monetization to be pay-per-analysis, pay-per-monitoring, or both?
- Should the first release be x402-only, or do you want a Stripe/MPP human checkout path in the same milestone?
- Do you want the marketplace listing to point at the current app, or a smaller dedicated paid API surface?
