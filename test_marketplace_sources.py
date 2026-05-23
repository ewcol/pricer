import unittest

from marketplace_sources import build_search_query, classify_market_segment, select_marketplace_sources


class MarketplaceSourcesTest(unittest.TestCase):
    def test_basic_apparel_sources(self):
        context = {
            "item_name": "L.L.Bean Aran Sweater",
            "brand": "L.L.Bean",
            "search_keywords": ["aran sweater", "crewneck"],
        }

        self.assertEqual(classify_market_segment(context), "basic_apparel")
        self.assertEqual(
            [source.key for source in select_marketplace_sources(context)],
            ["ebay", "poshmark", "mercari", "depop"],
        )

    def test_luxury_sources(self):
        context = {
            "item_name": "Gucci Wool Coat",
            "brand": "Gucci",
            "search_keywords": ["gucci coat", "designer outerwear"],
        }

        self.assertEqual(classify_market_segment(context), "luxury")
        self.assertEqual(
            [source.key for source in select_marketplace_sources(context)],
            ["ebay", "therealreal", "vestiaire"],
        )

    def test_sneakers_sources(self):
        context = ["jordan 1", "nike shoes"]

        self.assertEqual(classify_market_segment(context), "sneakers")
        self.assertEqual(
            [source.key for source in select_marketplace_sources(context)],
            ["ebay", "stockx"],
        )

    def test_streetwear_sources(self):
        context = {
            "item_name": "Supreme Box Logo Hoodie",
            "search_keywords": ["supreme hoodie", "streetwear"],
        }

        self.assertEqual(classify_market_segment(context), "streetwear")
        self.assertEqual(
            [source.key for source in select_marketplace_sources(context)],
            ["ebay", "depop", "poshmark", "mercari"],
        )

    def test_build_search_query(self):
        self.assertEqual(build_search_query(["  nike  ", "", " shoes "]), "nike shoes")


if __name__ == "__main__":
    unittest.main()
