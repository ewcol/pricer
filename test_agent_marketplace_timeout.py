import asyncio
import importlib
import os
import sys
import types
import unittest
from unittest import mock


class FakeGenaiClient:
    def __init__(self, *args, **kwargs):
        self.models = types.SimpleNamespace(generate_content=self._generate_content)

    def _generate_content(self, *args, **kwargs):
        return types.SimpleNamespace(text='{"item_name":"Item","brand":"Brand","condition_guess":"Good","search_keywords":["item"],"confidence":0.5,"reasoning":"ok"}')


class FakeLlmAgent:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class FakeRunner:
    def __init__(self, *args, **kwargs):
        pass


class FakeSessionService:
    def __init__(self, *args, **kwargs):
        pass


class FakeAgentTool:
    def __init__(self, *args, **kwargs):
        pass


class FakeNimbleAgent:
    def run(self, *args, **kwargs):
        return types.SimpleNamespace(data=types.SimpleNamespace(parsing=[]))


class FakeNimble:
    def __init__(self, *args, **kwargs):
        self.agent = FakeNimbleAgent()


class FakeImage:
    LANCZOS = object()

    def convert(self, *args, **kwargs):
        return self

    def thumbnail(self, *args, **kwargs):
        return None

    def save(self, *args, **kwargs):
        return None


def load_module():
    fake_google = types.ModuleType("google")
    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = FakeGenaiClient
    fake_genai_types = types.ModuleType("google.genai.types")
    fake_genai_types.Part = types.SimpleNamespace(from_bytes=lambda **kwargs: object())
    fake_genai.types = fake_genai_types
    fake_google.genai = fake_genai

    fake_adk_agents = types.ModuleType("google.adk.agents")
    fake_adk_agents.LlmAgent = FakeLlmAgent
    fake_adk_runners = types.ModuleType("google.adk.runners")
    fake_adk_runners.Runner = FakeRunner
    fake_adk_sessions = types.ModuleType("google.adk.sessions")
    fake_adk_sessions.InMemorySessionService = FakeSessionService
    fake_adk_tools = types.ModuleType("google.adk.tools")
    fake_adk_tools.AgentTool = FakeAgentTool

    fake_nimble = types.ModuleType("nimble_python")
    fake_nimble.Nimble = FakeNimble
    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: None
    fake_pil = types.ModuleType("PIL")
    fake_pil_image = types.ModuleType("PIL.Image")
    fake_pil_image.open = lambda *args, **kwargs: FakeImage()
    fake_pil_image.LANCZOS = FakeImage.LANCZOS
    fake_pil.Image = fake_pil_image

    with mock.patch.dict(
        sys.modules,
        {
            "google": fake_google,
            "google.genai": fake_genai,
            "google.genai.types": fake_genai_types,
            "google.adk": types.ModuleType("google.adk"),
            "google.adk.agents": fake_adk_agents,
            "google.adk.runners": fake_adk_runners,
            "google.adk.sessions": fake_adk_sessions,
            "google.adk.tools": fake_adk_tools,
            "nimble_python": fake_nimble,
            "dotenv": fake_dotenv,
            "PIL": fake_pil,
            "PIL.Image": fake_pil_image,
        },
    ):
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "x", "NIMBLE_API_KEY": "x"}, clear=False):
            sys.modules.pop("agent", None)
            module = importlib.import_module("agent")

    return module


class AgentMarketplaceTimeoutTest(unittest.TestCase):
    def test_grailed_source_times_out(self):
        module = load_module()
        source = module.MarketplaceSource("grailed", "grailed_sold_search", "query", 3, "Grailed")

        async def fake_to_thread(*args, **kwargs):
            await asyncio.sleep(0.05)
            return types.SimpleNamespace(data=types.SimpleNamespace(parsing=[]))

        with mock.patch.object(module.asyncio, "to_thread", fake_to_thread):
            result = asyncio.run(
                module._research_source_prices(source, "vintage nike jacket", timeout_seconds=0.01)
            )

        self.assertEqual(result["prices_found"], [])
        self.assertIn("timed out", result["note"])
        self.assertGreaterEqual(result["duration_seconds"], 0.0)

    def test_research_prices_skips_timed_out_source(self):
        module = load_module()
        ebay = module.MarketplaceSource("ebay", "ebay_search_2026_02_23_pbgj8oft", "query", 3, "eBay")
        grailed = module.MarketplaceSource("grailed", "grailed_sold_search", "query", 3, "Grailed")

        async def fake_research_source_prices(source, query, timeout_seconds=None):
            if source.key == "grailed":
                return {
                    "source": source.key,
                    "label": source.label,
                    "prices_found": [],
                    "source_urls": [],
                    "duration_seconds": 20.0,
                    "note": "Grailed search timed out after 20.0s.",
                    "timed_out": True,
                }
            return {
                "source": source.key,
                "label": source.label,
                "prices_found": [42.0],
                "source_urls": ["https://example.com"],
                "duration_seconds": 0.1,
                "note": "",
            }

        with mock.patch.object(module, "select_marketplace_sources", return_value=[ebay, grailed]):
            with mock.patch.object(module, "_research_source_prices", side_effect=fake_research_source_prices):
                result = asyncio.run(module.research_prices(["vintage nike jacket"], {"item_name": "Jacket"}))

        self.assertEqual(result["sources_used"], ["ebay"])
        self.assertEqual([entry["source"] for entry in result["source_breakdown"]], ["ebay"])
        self.assertEqual(result["prices_found"], [42.0])


if __name__ == "__main__":
    unittest.main()
