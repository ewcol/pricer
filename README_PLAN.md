# README Plan

## Goal
Write a root README for the project that explains the shipped product, how it works, how to run it, and why it is meaningful, without mentioning the hackathon prompt.

## Proposed Sections
1. Product overview
2. What the agent does
3. Architecture and tools
4. Payment and monetization
5. Demo flow
6. Setup and run instructions
7. API endpoints
8. Tracking and monitoring
9. Tests

## Content Direction
- Describe the project as an autonomous eBay pricing and listing agent that uses real web sources.
- Call out the current implementation details:
  - Gemini vision for item identification
  - Nimble marketplace research
  - x402-gated analysis route
  - CDP wallet setup and x402 fetch in the frontend
  - ClickHouse-backed tracking and price history
- Present x402 and CDP as the two sponsor tools already used in the shipped system.
- Mention the broader marketplace/distribution angle only if it is already supported by the code or clearly label it as future work.
- Keep the README practical and demo-oriented, with quick-start commands and a short 3-minute demo script.

## Output Style
- Direct and factual.
- No hackathon framing.
- No hype copy that overpromises beyond the implementation.
