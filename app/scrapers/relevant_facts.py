from bs4 import BeautifulSoup

from app.models import RelevantFact
from app.scrapers.html_utils import (
    cell_text,
    find_column,
    link_href,
    link_text,
    normalize_header,
)

RELEVANT_FACTS_URL = "https://www.fundamentus.com.br/fr.php"


def parse_relevant_facts(html: str) -> list[RelevantFact]:
    """Parse FR rows from the comunicados table."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="comunicados")
    if table is None:
        raise ValueError("Table with id 'comunicados' was not found")

    header_row = table.find("tr")
    if header_row is None:
        raise ValueError("Table 'comunicados' has no header row")

    header_cells = header_row.find_all(["th", "td"])
    headers = {
        normalize_header(cell.get_text(" ", strip=True)): index
        for index, cell in enumerate(header_cells)
    }
    date_index = find_column(headers, "Data")
    company_index = find_column(headers, "Empresa")
    type_index = find_column(headers, "Tipo")
    description_index = find_column(headers, "Descrição")
    download_index = find_column(headers, "Download")
    analysis_index = find_column(headers, "Analisar")

    facts: list[RelevantFact] = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) <= max(
            date_index,
            company_index,
            type_index,
            description_index,
            download_index,
            analysis_index,
        ):
            continue
        if cell_text(cells[type_index]).casefold() != "fr":
            continue

        facts.append(
            RelevantFact(
                date=cell_text(cells[date_index]),
                company=cell_text(cells[company_index]),
                description=cell_text(cells[description_index]),
                download_url=link_href(cells[download_index]),
                analysis=link_text(cells[analysis_index]),
            )
        )
    return facts


def format_relevant_facts(facts: list[RelevantFact]) -> str:
    """Format relevant facts using the public tool response contract."""
    return "\n\n----\n\n".join(
        "\n".join(
            [
                f"{fact['date']} - {fact['company']} ({fact['analysis']})",
                fact["description"],
                f"Url para Download do PDF: {fact['download_url']}",
            ]
        )
        for fact in facts
    )


class RelevantFactsScraper:
    """Fetch and parse relevant facts from Fundamentus."""

    def __init__(self, page_scraper) -> None:
        self._page_scraper = page_scraper

    async def fetch(self) -> str:
        html = await self._page_scraper.fetch_content(RELEVANT_FACTS_URL)
        return format_relevant_facts(parse_relevant_facts(html))