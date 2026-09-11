from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.dividends import (
    CompanyDividendsScraper,
    FIIIncomeScraper,
    format_company_dividends,
    format_fii_income,
    parse_company_dividends,
    parse_fii_income,
)

COMPANY_HTML = """
<table id="resultado" class="resultado rowstyle-par colstyle-col no-arrow">
	<thead>
		<tr>
			<th>Data</th>
			<th>Valor</th>
			<th>Tipo</th>
			<th>Data de Pagamento</th>
			<th>Por quantas ações</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>21/07/2026</td>
			<td>0,2546</td>
			<td>JRS CAP PROPRIO</td>
			<td>06/08/2026 </td>
			<td>1</td>
		</tr>
		<tr class="par">
			<td>20/04/2026</td>
			<td>0,2546</td>
			<td>JRS CAP PROPRIO</td>
			<td>07/05/2026 </td>
			<td>1</td>
		</tr>
		<tr>
			<td>17/10/2024</td>
			<td>0,0256</td>
			<td>DIVIDENDO</td>
			<td>08/11/2024 </td>
			<td>1</td>
		</tr>
	</tbody>
</table>
"""

FII_HTML = """
<table id="resultado" class="resultado rowstyle-par colstyle-col no-arrow">
	<thead>
		<tr>
			<th>Última Data Com</th>
			<th>Tipo</th>
			<th>Data de Pagamento</th>
			<th>Valor</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>30/06/2026</td>
			<td>Rendimento</td>
			<td>07/07/2026</td>
			<td>0,55</td>
		</tr>
		<tr class="par">
			<td>29/05/2026</td>
			<td>Rendimento</td>
			<td>08/06/2026</td>
			<td>0,55</td>
		</tr>
		<tr>
			<td>30/04/2026</td>
			<td>Rendimento</td>
			<td>08/05/2026</td>
			<td>0,60</td>
		</tr>
	</tbody>
</table>
"""


def test_parse_company_dividends() -> None:
    dividends = parse_company_dividends(COMPANY_HTML)
    assert len(dividends) == 3
    assert dividends[0] == {
        "date": "21/07/2026",
        "value": "0,2546",
        "type": "JRS CAP PROPRIO",
        "payment_date": "06/08/2026",
        "share_count": "1",
    }
    assert dividends[2]["type"] == "DIVIDENDO"


def test_format_company_dividends_all() -> None:
    dividends = parse_company_dividends(COMPANY_HTML)
    output = format_company_dividends(dividends)
    expected = (
        "PROVENTOS\n"
        "Data - Valor - Tipo - Data de Pagamento - Por quantas ações\n"
        "21/07/2026 - 0,2546 - JRS CAP PROPRIO - 06/08/2026 - 1\n"
        "20/04/2026 - 0,2546 - JRS CAP PROPRIO - 07/05/2026 - 1\n"
        "17/10/2024 - 0,0256 - DIVIDENDO - 08/11/2024 - 1"
    )
    assert output == expected


def test_format_company_dividends_limited() -> None:
    dividends = parse_company_dividends(COMPANY_HTML)
    output = format_company_dividends(dividends, last_n=1)
    expected = (
        "PROVENTOS\n"
        "Data - Valor - Tipo - Data de Pagamento - Por quantas ações\n"
        "21/07/2026 - 0,2546 - JRS CAP PROPRIO - 06/08/2026 - 1"
    )
    assert output == expected


def test_format_company_dividends_empty() -> None:
    assert (
        format_company_dividends([])
        == "Nenhum provento encontrado para o papel pesquisado."
    )


def test_parse_fii_income() -> None:
    incomes = parse_fii_income(FII_HTML)
    assert len(incomes) == 3
    assert incomes[0] == {
        "last_date_with": "30/06/2026",
        "type": "Rendimento",
        "payment_date": "07/07/2026",
        "value": "0,55",
    }


def test_format_fii_income_all() -> None:
    incomes = parse_fii_income(FII_HTML)
    output = format_fii_income(incomes)
    expected = (
        "PROVENTOS\n"
        "Última Data Com - Tipo - Data de Pagamento - Valor\n"
        "30/06/2026 - Rendimento - 07/07/2026 - 0,55\n"
        "29/05/2026 - Rendimento - 08/06/2026 - 0,55\n"
        "30/04/2026 - Rendimento - 08/05/2026 - 0,60"
    )
    assert output == expected


def test_format_fii_income_limited() -> None:
    incomes = parse_fii_income(FII_HTML)
    output = format_fii_income(incomes, last_n=2)
    expected = (
        "PROVENTOS\n"
        "Última Data Com - Tipo - Data de Pagamento - Valor\n"
        "30/06/2026 - Rendimento - 07/07/2026 - 0,55\n"
        "29/05/2026 - Rendimento - 08/06/2026 - 0,55"
    )
    assert output == expected


def test_format_fii_income_empty() -> None:
    assert (
        format_fii_income([])
        == "Nenhum provento encontrado para o papel pesquisado."
    )


@pytest.mark.asyncio
async def test_company_dividends_scraper_fetch() -> None:
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=COMPANY_HTML)
    page.close = AsyncMock()

    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)

    scraper = CompanyDividendsScraper(browser_context, timeout_ms=5000)
    result = await scraper.fetch("sanb3", last_n=1)

    page.goto.assert_awaited_once_with(
        "https://www.fundamentus.com.br/proventos.php?papel=SANB3&tipo=2",
        wait_until="domcontentloaded",
    )
    page.close.assert_awaited_once()
    assert "PROVENTOS" in result
    assert "21/07/2026 - 0,2546 - JRS CAP PROPRIO - 06/08/2026 - 1" in result


@pytest.mark.asyncio
async def test_fii_income_scraper_fetch() -> None:
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=FII_HTML)
    page.close = AsyncMock()

    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)

    scraper = FIIIncomeScraper(browser_context, timeout_ms=5000)
    result = await scraper.fetch("abcp11", last_n=2)

    page.goto.assert_awaited_once_with(
        "https://www.fundamentus.com.br/fii_proventos.php?papel=ABCP11&tipo=2",
        wait_until="domcontentloaded",
    )
    page.close.assert_awaited_once()
    assert "PROVENTOS" in result
    assert "30/06/2026 - Rendimento - 07/07/2026 - 0,55" in result
