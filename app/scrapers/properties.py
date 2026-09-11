from bs4 import BeautifulSoup, Tag
from playwright.async_api import BrowserContext

from app.models import PropertyListing
from app.scrapers.html_utils import cell_text, find_column, link_text, normalize_header

PROPERTIES_URL = "https://www.fundamentus.com.br/fii_imoveis.php"


def _is_hidden(row: Tag) -> bool:
    style = row.get("style", "").replace(" ", "").casefold()
    return row.has_attr("hidden") or "display:none" in style


def parse_properties(html: str) -> list[PropertyListing]:
    """Parse visible property rows from the Fundamentus property table."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tabelaFiiImoveis")
    if table is None:
        raise ValueError("Table with id 'tabelaFiiImoveis' was not found")

    header_row = table.find("tr")
    if header_row is None:
        raise ValueError("Table 'tabelaFiiImoveis' has no header row")

    headers = {
        normalize_header(cell.get_text(" ", strip=True)): index
        for index, cell in enumerate(header_row.find_all(["th", "td"]))
    }
    fund_index = find_column(headers, "FII")
    property_index = find_column(headers, "Imóvel", "Imovel")
    address_index = find_column(headers, "Endereço", "Endereco")
    characteristics_index = find_column(
        headers,
        "Outras características",
        "Outras caracteristicas",
    )

    properties: list[PropertyListing] = []
    for row in table.find_all("tr")[1:]:
        if _is_hidden(row):
            continue
        cells = row.find_all("td")
        required_index = max(
            fund_index,
            property_index,
            address_index,
            characteristics_index,
        )
        if len(cells) <= required_index:
            continue

        properties.append(
            {
                "fund": cell_text(cells[fund_index]),
                "property_name": link_text(cells[property_index]),
                "address": cell_text(cells[address_index]),
                "other_characteristics": cell_text(cells[characteristics_index]),
            }
        )
    return properties


def format_properties(properties: list[PropertyListing]) -> str:
    """Format properties using the public tool response contract."""
    formatted_properties = []
    for property_item in properties:
        lines = [
            f"{property_item['fund']} - {property_item['property_name']}",
            f"Endereço: {property_item['address']}",
        ]
        if property_item["other_characteristics"]:
            lines.append(
                "Outras características: "
                f"{property_item['other_characteristics']}"
            )
        formatted_properties.append("\n".join(lines))
    return "\n\n----\n\n".join(formatted_properties)


class PropertyScraper:
    """Search and parse properties from Fundamentus."""

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def search(self, text: str | None = None) -> str:
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(PROPERTIES_URL, wait_until="domcontentloaded")
            if text is not None:
                search_input = page.locator("#myInput")
                await search_input.fill(text)
                await search_input.dispatch_event("keyup")
            return format_properties(parse_properties(await page.content()))
        finally:
            await page.close()