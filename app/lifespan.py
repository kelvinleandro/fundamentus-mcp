from collections.abc import AsyncIterator

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from playwright.async_api import async_playwright

from app.config import load_settings
from app.models import BrowserResources


@lifespan
async def browser_lifespan(_: FastMCP) -> AsyncIterator[BrowserResources]:
    """Connect to Obscura and share its browser resources with MCP tools."""
    settings = load_settings()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(
            settings.obscura_cdp_url
        )
        owns_browser_context = not browser.contexts
        browser_context = (
            browser.contexts[0]
            if browser.contexts
            else await browser.new_context()
        )

        try:
            yield {
                "browser": browser,
                "browser_context": browser_context,
                "owns_browser_context": owns_browser_context,
            }
        finally:
            if owns_browser_context:
                await browser_context.close()
            await browser.close()
