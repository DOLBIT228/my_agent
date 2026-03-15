"""Internet search tool."""
from __future__ import annotations

from duckduckgo_search import DDGS


class SearchTool:
    def search(self, query: str, limit: int = 5) -> list[dict]:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=limit)
            return list(results)
