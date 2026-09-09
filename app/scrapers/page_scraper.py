from playwright.async_api import BrowserContext

EXAMPLE_PAGE_URL = "https://example.com"


class PageScraper:
    """Perform page-level browser operations independently of MCP."""

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def fetch_title(self) -> str:
        """Navigate to a page and return its document title."""
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(EXAMPLE_PAGE_URL, wait_until="domcontentloaded")
            return await page.title()
        finally:
            await page.close()

    async def fetch_content(self, url: str) -> str:
        """Navigate to a page and return its HTML content."""
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(url, wait_until="domcontentloaded")
            return await page.content()
        finally:
            await page.close()