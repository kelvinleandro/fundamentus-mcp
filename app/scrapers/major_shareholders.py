from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext

from app.models import Shareholder, ShareholderCategory

MAJOR_SHAREHOLDERS_URL = (
    "https://www.fundamentus.com.br/principais_acionistas.php?papel={}"
)


def _clean_text(element) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def parse_major_shareholders(html: str) -> list[ShareholderCategory]:
    """Parse major shareholder tables grouped by category (e.g. Ações Ordinárias, Capital Total)."""
    soup = BeautifulSoup(html, "html.parser")
    categories: list[ShareholderCategory] = []

    headers = soup.find_all("h1")
    for header in headers:
        category_name = _clean_text(header)
        if not category_name:
            continue

        table = header.find_next("table")
        if table is None:
            continue

        shareholders: list[Shareholder] = []
        tbody = table.find("tbody") or table
        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            name_cell = row.find("td", class_="res_nome") or cells[0]
            pct_cell = row.find("td", class_="res_pct") or cells[1]

            name = _clean_text(name_cell)
            percentage = _clean_text(pct_cell)

            if name and percentage:
                shareholders.append({"name": name, "percentage": percentage})

        if shareholders:
            categories.append(
                {
                    "category": category_name,
                    "shareholders": shareholders,
                }
            )

    return categories


def format_major_shareholders(categories: list[ShareholderCategory]) -> str:
    """Format major shareholders according to the requested text structure."""
    if not categories:
        return "Nenhum acionista encontrado para o papel pesquisado."

    sections: list[str] = []
    for category_item in categories:
        lines = [
            category_item["category"].upper(),
            "Acionista - Participação",
        ]
        for shareholder in category_item["shareholders"]:
            lines.append(f"{shareholder['name']} - {shareholder['percentage']}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


class MajorShareholdersScraper:
    """Scrape and parse major shareholders for a company on Fundamentus."""

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def fetch(self, ticker: str) -> str:
        clean_ticker = ticker.strip().upper()
        url = MAJOR_SHAREHOLDERS_URL.format(quote(clean_ticker, safe=""))
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            return format_major_shareholders(parse_major_shareholders(html))
        finally:
            await page.close()
