from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.security_search import (
    SecuritySearchScraper,
    format_security_matches,
    parse_security_matches,
)


TABLE_HTML = """
<table id="test1">
  <thead>
    <tr>
      <th>Papel</th>
      <th>Nome Comercial</th>
      <th>Razão Social</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="detalhes.php?papel=SANB3">SANB3</a></td>
      <td>Santander</td>
      <td>Banco Santander (Brasil) S.A.</td>
    </tr>
  </tbody>
</table>
"""

CURRENT_SECURITY_HTML = """
<div class="atual"><p>Você está vendo<strong>SANB3</strong></p></div>
"""


def create_page_mock(html: str) -> MagicMock:
  page = MagicMock()
  page.content = AsyncMock(return_value=html)
  page.goto = AsyncMock()
  page.close = AsyncMock()
  return page


def test_parse_security_matches_extracts_ticker_from_anchor() -> None:
    assert parse_security_matches(TABLE_HTML) == [
        {
            "ticker": "SANB3",
            "commercial_name": "Santander",
            "legal_name": "Banco Santander (Brasil) S.A.",
        }
    ]


def test_format_security_matches_has_actionable_introductory_text() -> None:
    matches = parse_security_matches(TABLE_HTML)

    assert format_security_matches(matches) == (
        "Encontrei estes papéis. Escolha um deles para consultar uma análise "
        "mais detalhada:\n"
        "SANB3 - Santander (Banco Santander (Brasil) S.A.)"
    )


@pytest.mark.asyncio
async def test_search_returns_current_security_paragraph() -> None:
    page = create_page_mock(CURRENT_SECURITY_HTML)
    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)
    scraper = SecuritySearchScraper(browser_context, timeout_ms=30_000)

    result = await scraper.search("SANB3")

    assert result == "Você está vendo<strong>SANB3</strong>"
    page.goto.assert_awaited_once_with(
        "https://www.fundamentus.com.br/detalhes.php?papel=SANB3",
        wait_until="domcontentloaded",
    )
    page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_quotes_spaces_and_accents_in_term() -> None:
    page = create_page_mock(CURRENT_SECURITY_HTML)
    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)
    scraper = SecuritySearchScraper(browser_context, timeout_ms=30_000)

    await scraper.search("São Carlos")

    page.goto.assert_awaited_once_with(
        "https://www.fundamentus.com.br/detalhes.php?papel=S%C3%A3o%20Carlos",
        wait_until="domcontentloaded",
    )
