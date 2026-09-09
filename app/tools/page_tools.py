from typing import cast

from fastmcp import Context, FastMCP

from app.config import Settings
from app.models import BrowserResources
from app.scrapers.page_scraper import PageScraper
from app.scrapers.relevant_facts import RelevantFactsScraper
from app.scrapers.properties import PropertyScraper
from app.scrapers.security_search import SecuritySearchScraper


def register_page_tools(mcp: FastMCP, settings: Settings) -> None:
    """Register page scraping tools on the MCP server."""

    @mcp.tool
    async def fetch_page(ctx: Context) -> str:
        """Fetch the configured example page and return its document title."""
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = PageScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.fetch_title()

    @mcp.tool
    async def get_relevant_facts(ctx: Context) -> str:
        """Return the latest Fundamentus relevant facts with PDF links."""
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = PageScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await RelevantFactsScraper(scraper).fetch()

    @mcp.tool
    async def search_properties(
        ctx: Context,
        text: str | None = None,
    ) -> str:
        """Search Fundamentus properties by text and return matching rows."""
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = PropertyScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.search(text)

    @mcp.tool
    async def search_security(ctx: Context, term: str) -> str:
        """Search for an action, company, or FII by ticker or name."""
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = SecuritySearchScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.search(term)
