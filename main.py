import os
from typing import TypedDict, cast
from collections.abc import AsyncIterator

from fastmcp import Context, FastMCP
from fastmcp.server.lifespan import lifespan
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from dotenv import load_dotenv

load_dotenv()


class AppContext(TypedDict):
    playwright: Playwright
    browser: Browser
    browser_context: BrowserContext


@lifespan
async def browser_lifespan(_: FastMCP) -> AsyncIterator[AppContext]:
    """Keep the CDP browser connection alive for the lifetime of the MCP server."""
    cdp_url = os.environ["OBSCURA_CDP_URL"]

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(cdp_url)
        browser_context = (
            browser.contexts[0]
            if browser.contexts
            else await browser.new_context()
        )

        try:
            yield {
                "playwright": playwright,
                "browser": browser,
                "browser_context": browser_context,
            }
        finally:
            await browser.close()


mcp = FastMCP("Fundamentus", lifespan=browser_lifespan)


@mcp.tool
async def fetch_page(ctx: Context) -> str:
    """Fetch https://example.com and return its document title."""
    browser_context = cast(AppContext, ctx.lifespan_context)["browser_context"]
    page: Page = await browser_context.new_page()

    try:
        await page.goto("https://example.com", wait_until="domcontentloaded")
        return await page.title()
    finally:
        await page.close()


if __name__ == "__main__":
    mcp.run()
