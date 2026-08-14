import unittest

from search import SearchService


class SearchServiceTests(unittest.TestCase):
    def test_returns_backend_results(self) -> None:
        service = SearchService(lambda query: [query.upper()])
        self.assertEqual(service.search("alpha"), ["ALPHA"])


if __name__ == "__main__":
    unittest.main()
