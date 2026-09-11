from collections.abc import Sequence
import json
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag
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


def _text(element: Tag) -> str:
    for help_element in element.select(".help.tips"):
        help_element.decompose()
    return " ".join(element.get_text(" ", strip=True).split())


def _table_pairs(table: Tag, *, include_empty: bool = False) -> list[tuple[str, str]]:
    pairs = []
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        for index in range(0, len(cells) - 1, 2):
            label = _text(cells[index])
            value = _text(cells[index + 1])
            if (
                label
                and (value or include_empty)
                and not any(
                    class_name.startswith("nivel")
                    for class_name in cells[index].get("class", [])
                )
            ):
                pairs.append((label, value))
    return pairs


def _is_section_cell(cell: Tag, title: str) -> bool:
    return title.casefold() in _text(cell).casefold() and any(
        class_name.startswith("nivel") for class_name in cell.get("class", [])
    )


def _row_value_pairs(cells: Sequence[Tag]) -> list[tuple[str, str]]:
    pairs = []
    for index in range(0, len(cells) - 1, 2):
        label = _text(cells[index])
        value = _text(cells[index + 1])
        if label and value:
            pairs.append((label, value))
    return pairs


def _parse_fii_details(html: str) -> dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table.w728")
    if len(tables) < 5:
        raise ValueError("Expected at least five FII detail tables")

    general: dict[str, str] = {}
    for label, value in _table_pairs(
        tables[0], include_empty=True
    ) + _table_pairs(tables[1], include_empty=True):
        general["Cotacao" if label == "Cotação" else label] = value

    oscillations: dict[str, str] = {}
    indicators: dict[str, str] = {}
    results = {"ultimos_12_meses": {}, "ultimos_3_meses": {}}
    balance: dict[str, str] = {}
    metrics_table = tables[2]
    right_section = "indicators"

    for row in metrics_table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        if len(cells) >= 2:
            left_label = _text(cells[0])
            left_value = _text(cells[1])
            if left_label and left_value and not any(
                class_name.startswith("nivel")
                for class_name in cells[0].get("class", [])
            ):
                oscillations[left_label] = left_value

        if any(_is_section_cell(cell, "Resultado") for cell in cells):
            right_section = "results"
        elif any(_is_section_cell(cell, "Balanço Patrimonial") for cell in cells):
            right_section = "balance"

        right_pairs = _row_value_pairs(cells[2:])
        right_pairs = [
            pair
            for pair in right_pairs
            if not pair[0].casefold().startswith("últimos")
        ]
        if right_section == "indicators":
            for label, value in right_pairs:
                indicators[label] = value
        elif right_section == "results":
            if right_pairs:
                results["ultimos_12_meses"][right_pairs[0][0]] = right_pairs[0][1]
            if len(right_pairs) > 1:
                results["ultimos_3_meses"][right_pairs[1][0]] = right_pairs[1][1]
        elif right_section == "balance":
            for label, value in right_pairs:
                balance[label] = value

    properties: dict[str, str] = {}
    for row in tables[4].find_all("tr"):
        cells = row.find_all("td")
        for index in range(0, len(cells) - 1, 2):
            label = _text(cells[index])
            value = _text(cells[index + 1])
            if label and value:
                properties[label] = value

    return {
        "geral": general,
        "oscilacoes": oscillations,
        "indicadores": indicators,
        "resultado": results,
        "balanco_patrimonial": balance,
        "imoveis": properties,
    }


def _parse_security_details(html: str) -> dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table.w728")
    if len(tables) < 5:
        raise ValueError("Expected at least five security detail tables")

    general: dict[str, str] = {}
    for label, value in _table_pairs(tables[0]) + _table_pairs(tables[1]):
        general[label] = value

    oscillations: dict[str, str] = {}
    indicators: dict[str, str] = {}
    metrics_table = tables[2]
    for row in metrics_table.find_all("tr")[1:]:
        cells = row.find_all("td")
        for index in range(0, len(cells) - 1, 2):
            label = _text(cells[index])
            value = _text(cells[index + 1])
            if not label:
                continue
            if index == 0:
                key = "mes" if label == "Mês" else label.casefold()
                if value:
                    oscillations[key] = value
            elif value:
                indicators[label] = value

    balance = dict(_table_pairs(tables[3]))

    results: dict[str, dict[str, str]] = {
        "ultimos_12_meses": {},
        "ultimos_3_meses": {},
    }
    result_table = tables[4]
    for row in result_table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 4 and not any("nivel" in cell.get("class", []) for cell in cells):
            left_label = _text(cells[0])
            left_value = _text(cells[1])
            right_label = _text(cells[2])
            right_value = _text(cells[3])
            if left_label and left_value:
                results["ultimos_12_meses"][left_label] = left_value
            if right_label and right_value:
                results["ultimos_3_meses"][right_label] = right_value

    return {
        "geral": general,
        "oscilacoes": oscillations,
        "indicadores_fundamentalistas": indicators,
        "dados_balanco_patrimonial": balance,
        "dados_demonst_resultados": results,
    }


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
                soup = BeautifulSoup(html, "html.parser")
                first_table_text = _text(soup.select_one("table.w728") or soup)
                details = (
                    _parse_fii_details(html)
                    if "FII" in first_table_text
                    else _parse_security_details(html)
                )
                return json.dumps(
                    details,
                    ensure_ascii=False,
                    indent=2,
                )
            return format_security_matches(parse_security_matches(html))
        finally:
            await page.close()