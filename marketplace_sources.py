"""Marketplace source selection for resale comps."""
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class MarketplaceSource:
    key: str
    agent_name: str
    param_name: str
    priority: int
    label: str


SOURCE_SPECS: dict[str, MarketplaceSource] = {
    "ebay": MarketplaceSource("ebay", "ebay_search_2026_02_23_pbgj8oft", "query", 3, "eBay"),
    "poshmark": MarketplaceSource("poshmark", "poshmark_sold_search", "query", 1, "Poshmark"),
    "depop": MarketplaceSource("depop", "depop_sold_search", "query", 1, "Depop"),
    "mercari": MarketplaceSource("mercari", "mercari_us_sold_search", "keyword", 1, "Mercari"),
    "therealreal": MarketplaceSource(
        "therealreal", "therealreal_sold_search", "query", 2, "The RealReal"
    ),
    "vestiaire": MarketplaceSource("vestiaire", "vestiaire_sold_search", "query", 2, "Vestiaire"),
    "stockx": MarketplaceSource("stockx", "stockx_sold_search", "query", 2, "StockX"),
}


CATEGORY_TO_SOURCES: dict[str, list[str]] = {
    "basic_apparel": ["ebay", "poshmark", "mercari", "depop"],
    "streetwear": ["ebay", "depop", "poshmark", "mercari"],
    "luxury": ["ebay", "therealreal", "vestiaire"],
    "sneakers": ["ebay", "stockx"],
}

LUXURY_TOKENS = {
    "gucci",
    "prada",
    "chanel",
    "louis vuitton",
    "lv",
    "hermes",
    "celine",
    "dior",
    "balenciaga",
    "burberry",
    "loro piana",
    "moncler",
    "saint laurent",
    "ysl",
    "fendi",
    "valentino",
    "givenchy",
    "loewe",
    "bottega",
    "versace",
    "mcm",
    "the row",
    "jimmy choo",
    "salvatore ferragamo",
}

STREETWEAR_TOKENS = {
    "supreme",
    "stussy",
    "bape",
    "palace",
    "off-white",
    "fear of god",
    "essentials",
    "kith",
    "carhartt wip",
    "wtaps",
    "undercover",
    "acronym",
    "comme des garcons",
    "noah",
    "eric emanuel",
    "amiri",
    "chrome hearts",
    "vetements",
    "rick owens",
    "needles",
    "neighborhood",
    "human made",
}

SNEAKER_TOKENS = {
    "sneaker",
    "sneakers",
    "shoe",
    "shoes",
    "jordan",
    "dunk",
    "yeezy",
    "air max",
    "air force",
    "new balance",
    "adidas",
    "nike",
    "asics",
    "salomon",
    "converse",
    "vans",
}


def build_search_query(search_keywords: Iterable[str]) -> str:
    return " ".join(keyword.strip() for keyword in search_keywords if str(keyword).strip())


def _collect_text_terms(search_context: object) -> list[str]:
    if isinstance(search_context, Mapping):
        terms: list[str] = []
        for key in ("item_name", "brand", "title"):
            value = search_context.get(key)
            if value:
                terms.append(str(value))
        keywords = search_context.get("search_keywords")
        if isinstance(keywords, Sequence) and not isinstance(keywords, (str, bytes)):
            terms.extend(str(keyword) for keyword in keywords if str(keyword).strip())
        return terms

    if isinstance(search_context, Sequence) and not isinstance(search_context, (str, bytes)):
        return [str(term) for term in search_context if str(term).strip()]

    if search_context:
        return [str(search_context)]

    return []


def build_search_text(search_context: object) -> str:
    return " ".join(_collect_text_terms(search_context)).lower()


def classify_market_segment(search_context: object) -> str:
    text = build_search_text(search_context)

    if any(token in text for token in SNEAKER_TOKENS):
        return "sneakers"

    if any(token in text for token in LUXURY_TOKENS):
        return "luxury"

    if any(token in text for token in STREETWEAR_TOKENS):
        return "streetwear"

    return "basic_apparel"


def select_marketplace_sources(search_context: object) -> list[MarketplaceSource]:
    segment = classify_market_segment(search_context)
    source_keys = CATEGORY_TO_SOURCES[segment]
    return [SOURCE_SPECS[key] for key in source_keys]
