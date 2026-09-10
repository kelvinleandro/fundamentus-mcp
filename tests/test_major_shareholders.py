from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.major_shareholders import (
    MajorShareholdersScraper,
    format_major_shareholders,
    parse_major_shareholders,
)

SAMPLE_HTML = """
<div style="float:left; margin-right: 17px;">
	<h1>Ações Ordinárias</h1>
	<table id="acoesordinarias" class="resultado rowstyle-par colstyle-col no-arrow" border="0" cellpadding="0"
		cellspacing="0">
		<thead>
			<tr>
				<th class="fd-column-0 sortable-text reverseSort"><a href="#">Acionista</a></th>
				<th class="fd-column-1 sortable-numeric"><a href="#">Participação</a></th>
			</tr>
		</thead>
		<tbody>
			<tr class="">
				<td class="res_nome"><span>Banco Santander S/A Espanha</span></td>
				<td class="res_pct">42,25%</td>
			</tr>
			<tr class="par">
				<td class="res_nome"><span>Investidores Institucionais</span></td>
				<td class="res_pct">28,44%</td>
			</tr>
		</tbody>
	</table>
</div>
<div>
	<h1>Capital Total</h1>
	<table id="capitaltotal" class="resultado rowstyle-par colstyle-col no-arrow" border="0" cellpadding="0"
		cellspacing="0">
		<thead>
			<tr>
				<th class="fd-column-0 sortable-text reverseSort"><a href="#">Acionista</a></th>
				<th class="fd-column-1 sortable-numeric "><a href="#">Participação</a></th>
			</tr>
		</thead>
		<tbody>
			<tr class="">
				<td class="res_nome"><span>Banco Santander S/A Espanha</span></td>
				<td class="res_pct">41,87%</td>
			</tr>
			<tr class="par">
				<td class="res_nome"><span>Investidores Institucionais</span></td>
				<td class="res_pct">28,34%</td>
			</tr>
		</tbody>
	</table>
</div>
"""


def test_parse_major_shareholders_extracts_categories_and_rows() -> None:
    categories = parse_major_shareholders(SAMPLE_HTML)

    assert len(categories) == 2
    assert categories[0]["category"] == "Ações Ordinárias"
    assert categories[0]["shareholders"] == [
        {"name": "Banco Santander S/A Espanha", "percentage": "42,25%"},
        {"name": "Investidores Institucionais", "percentage": "28,44%"},
    ]

    assert categories[1]["category"] == "Capital Total"
    assert categories[1]["shareholders"] == [
        {"name": "Banco Santander S/A Espanha", "percentage": "41,87%"},
        {"name": "Investidores Institucionais", "percentage": "28,34%"},
    ]


def test_format_major_shareholders_matches_expected_output() -> None:
    categories = parse_major_shareholders(SAMPLE_HTML)
    formatted = format_major_shareholders(categories)

    expected = (
        "AÇÕES ORDINÁRIAS\n"
        "Acionista - Participação\n"
        "Banco Santander S/A Espanha - 42,25%\n"
        "Investidores Institucionais - 28,44%\n\n"
        "CAPITAL TOTAL\n"
        "Acionista - Participação\n"
        "Banco Santander S/A Espanha - 41,87%\n"
        "Investidores Institucionais - 28,34%"
    )
    assert formatted == expected


def test_format_major_shareholders_empty() -> None:
    assert (
        format_major_shareholders([])
        == "Nenhum acionista encontrado para o papel pesquisado."
    )


@pytest.mark.asyncio
async def test_scraper_fetch_navigates_and_returns_formatted_text() -> None:
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=SAMPLE_HTML)
    page.close = AsyncMock()

    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)

    scraper = MajorShareholdersScraper(browser_context, timeout_ms=5000)
    result = await scraper.fetch("sanb3")

    page.goto.assert_awaited_once_with(
        "https://www.fundamentus.com.br/principais_acionistas.php?papel=SANB3",
        wait_until="domcontentloaded",
    )
    page.close.assert_awaited_once()
    assert "AÇÕES ORDINÁRIAS" in result
    assert "Banco Santander S/A Espanha - 42,25%" in result
