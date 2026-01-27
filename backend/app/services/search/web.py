"""Web search service with multiple providers."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog
from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.core.config import settings

logger = structlog.get_logger()


class SearchProvider(str, Enum):
    """Supported search providers."""

    TAVILY = "tavily"
    SERP = "serp"
    GOOGLE = "google"
    BING = "bing"
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str
    content: str | None = None
    score: float | None = None
    published_date: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Response from a search query."""

    query: str
    provider: SearchProvider
    results: list[SearchResult]
    total_results: int
    search_time_ms: int
    answer: str | None = None  # AI-generated answer (Tavily)
    images: list[dict[str, str]] = field(default_factory=list)
    related_queries: list[str] = field(default_factory=list)


class BaseSearchProvider(ABC):
    """Base class for search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs,
    ) -> list[SearchResult]:
        """Execute a search query."""
        pass


class TavilySearchProvider(BaseSearchProvider):
    """Tavily search provider with AI-enhanced results."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",  # basic or advanced
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_images: bool = False,
        **kwargs,
    ) -> tuple[list[SearchResult], dict[str, Any]]:
        """Execute a Tavily search."""
        if not self.api_key:
            logger.error("Tavily API key not configured")
            return [], {}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": search_depth,
                        "include_answer": include_answer,
                        "include_raw_content": include_raw_content,
                        "include_images": include_images,
                        "max_results": max_results,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        content=item.get("raw_content"),
                        score=item.get("score"),
                        published_date=item.get("published_date"),
                    ))

                extra = {
                    "answer": data.get("answer"),
                    "images": data.get("images", []),
                    "response_time": data.get("response_time"),
                }

                return results, extra

            except Exception as e:
                logger.error("Tavily search failed", error=str(e))
                return [], {}


class SerpAPIProvider(BaseSearchProvider):
    """SerpAPI provider for Google/Bing search."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.SERP_API_KEY
        self.base_url = "https://serpapi.com/search"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        engine: str = "google",
        **kwargs,
    ) -> list[SearchResult]:
        """Execute a SerpAPI search."""
        if not self.api_key:
            logger.error("SerpAPI key not configured")
            return []

        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "api_key": self.api_key,
                    "q": query,
                    "engine": engine,
                    "num": max_results,
                }
                params.update(kwargs)

                response = await client.get(
                    self.base_url,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("organic_results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source=item.get("source"),
                        metadata={
                            "position": item.get("position"),
                            "displayed_link": item.get("displayed_link"),
                        },
                    ))

                return results

            except Exception as e:
                logger.error("SerpAPI search failed", error=str(e))
                return []


class BraveSearchProvider(BaseSearchProvider):
    """Brave Search API provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.BRAVE_API_KEY
        self.base_url = "https://api.search.brave.com/res/v1"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs,
    ) -> list[SearchResult]:
        """Execute a Brave search."""
        if not self.api_key:
            logger.error("Brave API key not configured")
            return []

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/web/search",
                    params={
                        "q": query,
                        "count": max_results,
                    },
                    headers={
                        "X-Subscription-Token": self.api_key,
                        "Accept": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("description", ""),
                        metadata={
                            "age": item.get("age"),
                            "language": item.get("language"),
                        },
                    ))

                return results

            except Exception as e:
                logger.error("Brave search failed", error=str(e))
                return []


class ContentScraper:
    """Scraper for extracting content from web pages."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def scrape(self, url: str) -> str | None:
        """Scrape content from a URL."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; NexusAI/1.0; +https://nexusai.dev)",
                    },
                )
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Remove script and style elements
                for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    element.decompose()

                # Get main content
                main_content = soup.find("main") or soup.find("article") or soup.find("body")

                if main_content:
                    text = main_content.get_text(separator="\n", strip=True)
                    # Clean up whitespace
                    lines = [line.strip() for line in text.split("\n") if line.strip()]
                    return "\n".join(lines)

                return None

            except Exception as e:
                logger.warning("Failed to scrape URL", url=url, error=str(e))
                return None

    async def scrape_multiple(
        self,
        urls: list[str],
        max_concurrent: int = 5,
    ) -> dict[str, str | None]:
        """Scrape multiple URLs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url: str) -> tuple[str, str | None]:
            async with semaphore:
                content = await self.scrape(url)
                return url, content

        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)

        return dict(results)


class WebSearchService:
    """Main web search service with provider abstraction."""

    def __init__(self):
        self._providers: dict[SearchProvider, BaseSearchProvider] = {}
        self._scraper = ContentScraper()
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize available providers."""
        if settings.TAVILY_API_KEY:
            self._providers[SearchProvider.TAVILY] = TavilySearchProvider()

        if settings.SERP_API_KEY:
            self._providers[SearchProvider.SERP] = SerpAPIProvider()

        if settings.BRAVE_API_KEY:
            self._providers[SearchProvider.BRAVE] = BraveSearchProvider()

    async def search(
        self,
        query: str,
        provider: SearchProvider | None = None,
        max_results: int = 10,
        include_content: bool = False,
        **kwargs,
    ) -> SearchResponse:
        """Execute a web search."""
        start_time = datetime.now(UTC)

        # Select provider
        if provider and provider in self._providers:
            selected_provider = provider
        elif self._providers:
            # Use first available provider (prefer Tavily)
            if SearchProvider.TAVILY in self._providers:
                selected_provider = SearchProvider.TAVILY
            else:
                selected_provider = list(self._providers.keys())[0]
        else:
            logger.error("No search providers configured")
            return SearchResponse(
                query=query,
                provider=SearchProvider.TAVILY,
                results=[],
                total_results=0,
                search_time_ms=0,
            )

        # Execute search
        provider_instance = self._providers[selected_provider]

        if selected_provider == SearchProvider.TAVILY:
            results, extra = await provider_instance.search(
                query, max_results, **kwargs
            )
            answer = extra.get("answer")
            images = extra.get("images", [])
        else:
            results = await provider_instance.search(query, max_results, **kwargs)
            answer = None
            images = []

        # Optionally scrape content
        if include_content and results:
            urls = [r.url for r in results[:5]]  # Limit to first 5
            contents = await self._scraper.scrape_multiple(urls)

            for result in results:
                if result.url in contents:
                    result.content = contents[result.url]

        search_time = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

        return SearchResponse(
            query=query,
            provider=selected_provider,
            results=results,
            total_results=len(results),
            search_time_ms=search_time,
            answer=answer,
            images=images,
        )

    async def search_and_summarize(
        self,
        query: str,
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Search and provide AI-summarized results."""
        # Use Tavily if available (has built-in summarization)
        response = await self.search(
            query,
            provider=SearchProvider.TAVILY,
            max_results=max_results,
            include_answer=True,
        )

        return {
            "query": query,
            "answer": response.answer,
            "sources": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                }
                for r in response.results
            ],
            "search_time_ms": response.search_time_ms,
        }

    def get_available_providers(self) -> list[SearchProvider]:
        """Get list of available providers."""
        return list(self._providers.keys())


# Global service instance
web_search_service = WebSearchService()
