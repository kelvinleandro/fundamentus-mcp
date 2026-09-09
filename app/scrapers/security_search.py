from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext

from app.models import SecurityMatch
from app.scrapers.html_utils import cell_text, find_column, link_text, normalize_header

SECURITY_DETAILS_URL = "https://www.fundamentus.com.br/detalhes.php?papel={}"


def _parse_current_security(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    current_paragraph = soup.select_one("div.atual p")
    if current_paragraph is None:
        return None
    return current_paragraph.decode_contents().strip()


def parse_security_matches(html: str) -> list[SecurityMatch]:
    """Parse security choices from the details search table."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="test1")
    if table is None:
        raise ValueError("Table with id 'test1' was not found")

    header_row = table.find("tr")
    if header_row is None:
        raise ValueError("Table 'test1' has no header row")

    headers = {
        normalize_header(cell.get_text(" ", strip=True)): index
        for index, cell in enumerate(header_row.find_all(["th", "td"]))
    }
    ticker_index = find_column(headers, "Papel")
    commercial_name_index = find_column(headers, "Nome Comercial")
    legal_name_index = find_column(headers, "Razão Social", "Razao Social")

    matches: list[SecurityMatch] = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        required_index = max(ticker_index, commercial_name_index, legal_name_index)
        if len(cells) <= required_index:
            continue

        matches.append(
            {
                "ticker": link_text(cells[ticker_index]),
                "commercial_name": cell_text(cells[commercial_name_index]),
                "legal_name": cell_text(cells[legal_name_index]),
            }
        )
    return matches


def format_security_matches(matches: list[SecurityMatch]) -> str:
    """Format security choices for a more detailed search."""
    if not matches:
        return "Nenhum papel encontrado para o termo pesquisado."

    entries = "\n\n----\n\n".join(
        f"{match['ticker']} - {match['commercial_name']} ({match['legal_name']})"
        for match in matches
    )
    return (
        "Encontrei estes papéis. Escolha um deles para consultar uma análise "
        "mais detalhada:\n"
        f"{entries}"
    )


class SecuritySearchScraper:
    """Search for an action, company, or FII on Fundamentus."""

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def search(self, term: str) -> str:
        encoded_term = quote(term, safe="")
        url = SECURITY_DETAILS_URL.format(encoded_term)
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            current_security = _parse_current_security(html)
            if current_security is not None:
                return current_security
            return format_security_matches(parse_security_matches(html))
        finally:
            await page.close()