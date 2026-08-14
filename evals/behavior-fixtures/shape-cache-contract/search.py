from collections.abc import Callable


class SearchService:
    def __init__(self, backend: Callable[[str], list[str]]) -> None:
        self._backend = backend

    def search(self, query: str) -> list[str]:
        return self._backend(query)
