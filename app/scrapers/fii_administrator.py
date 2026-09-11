import json
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext

from app.models import FIIAdministratorDetails
from app.scrapers.html_utils import cell_text

FII_ADMINISTRATOR_URL = (
    "https://www.fundamentus.com.br/fii_administrador.php?papel={}"
)


def parse_fii_administrator(html: str) -> FIIAdministratorDetails:
    """Parse administrator details and remuneration policy from fii_administrador.php."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.w728") or soup.find("table")
    if table is None:
        return {"administracao": {}, "politica_remuneracao": ""}

    admin_data: dict[str, str] = {}
    remuneracao_text = ""
    current_section = "administracao"

    for row in table.find_all("tr"):
        nivel_cell = row.find("td", class_=lambda c: c and "nivel1" in c)
        if nivel_cell:
            title = cell_text(nivel_cell).casefold()
            if "remunera" in title:
                current_section = "remuneracao"
            else:
                current_section = "administracao"
            continue

        if current_section == "administracao":
            label_cell = row.find("td", class_=lambda c: c and "label" in c)
            data_cell = row.find("td", class_=lambda c: c and "data" in c)
            if label_cell and data_cell:
                label = cell_text(label_cell)
                value = cell_text(data_cell)
                if label:
                    admin_data[label] = value
        elif current_section == "remuneracao":
            remuneracao_cell = row.find(
                "span", class_=lambda c: c and "remuneracao" in c
            ) or row.find("td")
            if remuneracao_cell:
                text = cell_text(remuneracao_cell)
                if text:
                    remuneracao_text = text

    return {
        "administracao": admin_data,
        "politica_remuneracao": remuneracao_text,
    }


def format_fii_administrator_json(data: FIIAdministratorDetails) -> str:
    """Serialize the FII administrator details to formatted JSON."""
    return json.dumps(data, ensure_ascii=False, indent=2)


class FIIAdministratorScraper:
    """Scrape and parse administrator details for a specific FII."""

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def fetch(self, ticker: str) -> str:
        clean_ticker = ticker.strip().upper()
        url = FII_ADMINISTRATOR_URL.format(quote(clean_ticker, safe=""))
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            return format_fii_administrator_json(parse_fii_administrator(html))
        finally:
            await page.close()
