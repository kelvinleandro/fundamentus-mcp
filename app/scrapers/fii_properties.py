import json
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext

from app.models import FIIPropertyDetail
from app.scrapers.html_utils import (
    cell_text,
    find_column,
    link_text,
    normalize_header,
)

FII_PROPERTIES_URL = (
    "https://www.fundamentus.com.br/fii_imoveis_detalhes.php?papel={}"
)


def _clean_numeric_percentage(cell) -> str:
    """Extract text from a cell while decomposing auxiliary interactive/chart icons."""
    for tag in list(cell.find_all(["a", "img", "svg"])):
        if tag.attrs is not None:
            onclick = tag.attrs.get("onclick", "")
            if (isinstance(onclick, str) and "obtemGrafico" in onclick) or tag.name in {"img", "svg"}:
                tag.decompose()
    return cell_text(cell)


def parse_fii_properties(html: str) -> list[FIIPropertyDetail]:
    """Parse property records from the fii_imoveis_detalhes.php table."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="resultado")
    if table is None:
        return []

    header_row = table.find("tr")
    if header_row is None:
        return []

    headers = {
        normalize_header(cell.get_text(" ", strip=True)): index
        for index, cell in enumerate(header_row.find_all(["th", "td"]))
    }

    try:
        imovel_index = find_column(headers, "Imóvel")
        endereco_index = find_column(headers, "Endereço")
        area_index = find_column(headers, "Área")
        unidades_index = find_column(headers, "Num Unidades")
        caracteristicas_index = find_column(headers, "Características")
        ocupacao_index = find_column(headers, "% tx ocupação")
        inadimplencia_index = find_column(headers, "% inadimplência")
        receitas_index = find_column(headers, "% das receitas do fii")
    except ValueError:
        # Fallback to standard positional indexes if headers slightly differ
        imovel_index, endereco_index, area_index, unidades_index = 0, 1, 2, 3
        caracteristicas_index, ocupacao_index, inadimplencia_index, receitas_index = 4, 5, 6, 7

    properties: list[FIIPropertyDetail] = []
    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 8:
            continue

        imovel = cell_text(cells[imovel_index])
        endereco = link_text(cells[endereco_index]) or cell_text(cells[endereco_index])
        area = cell_text(cells[area_index])
        num_unidades = cell_text(cells[unidades_index])
        caracteristicas = cell_text(cells[caracteristicas_index])
        taxa_ocupacao = _clean_numeric_percentage(cells[ocupacao_index])
        inadimplencia = cell_text(cells[inadimplencia_index])
        participacao_receitas = cell_text(cells[receitas_index])

        if imovel or endereco:
            properties.append(
                {
                    "imovel": imovel,
                    "endereco": endereco,
                    "area": area,
                    "num_unidades": num_unidades,
                    "caracteristicas": caracteristicas,
                    "taxa_ocupacao": taxa_ocupacao,
                    "inadimplencia": inadimplencia,
                    "participacao_receitas": participacao_receitas,
                }
            )

    return properties


def format_fii_properties_json(properties: list[FIIPropertyDetail]) -> str:
    """Serialize the FII property details to formatted JSON."""
    return json.dumps(properties, ensure_ascii=False, indent=2)


class FIIPropertiesScraper:
    """Scrape and parse physical property details for a specific FII."""

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def fetch(self, ticker: str) -> str:
        clean_ticker = ticker.strip().upper()
        url = FII_PROPERTIES_URL.format(quote(clean_ticker, safe=""))
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            return format_fii_properties_json(parse_fii_properties(html))
        finally:
            await page.close()
