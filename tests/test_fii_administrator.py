import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.fii_administrator import (
    FIIAdministratorScraper,
    format_fii_administrator_json,
    parse_fii_administrator,
)

FII_ADMIN_HTML = """
<table class="w728">
	<tbody>
		<tr>
			<td class="nivel1" colspan="2"><span class="txt">Administração</span></td>
		</tr>
		<tr>
			<td class="label w3"><span class="label">Nome</span></td>
			<td class="data w7" colspan="3"><span class="txt">MODAL DTVM LTDA</span></td>
		</tr>
		<tr>
			<td class="label w3"><span class="label">CNPJ do Fundo</span></td>
			<td class="data w7"><span class="txt">35.765.826/0001-26</span></td>
		</tr>
		<tr>
			<td class="label w3"><span class="label">CNPJ do Administrador</span></td>
			<td class="data w7"><span class="txt">36.864.992/0001-42</span></td>
		</tr>
		<tr>
			<td class="label w3"><span class="label">Telefone</span></td>
			<td class="data w7"><span class="txt">(11) 3509-0600</span></td>
		</tr>
		<tr>
			<td class="label w3"><span class="label">E-mail</span></td>
			<td class="data w7"><span class="txt">infolegal@apexgroup.com</span></td>
		</tr>
		<tr>
			<td class="label w3"><span class="label">Site</span></td>
			<td class="data w7"><span class="txt">www.apexgroup.com/apex-brazil/</span></td>
		</tr>
		<tr>
			<td class="label w3"><span class="label">Tx administração sobre o PL</span></td>
			<td class="data w7"><span class="txt">0,91%</span></td>
		</tr>
		<tr>
			<td class="label w3"><span class="label">Tx administração sobre o Valor de Mercado</span></td>
			<td class="data w7"><span class="txt">1,46%</span></td>
		</tr>
		<tr>
			<td class="nivel1" colspan="2"><span class="txt">Política de Remuneração</span></td>
		</tr>
		<tr>
			<td class="data w7" colspan="2" style="padding:10px;"><span class="txt remuneracao">O Administrador fará jus a uma taxa anual equivalente de até 0,75%.</span></td>
		</tr>
	</tbody>
</table>
"""


def test_parse_fii_administrator() -> None:
    data = parse_fii_administrator(FII_ADMIN_HTML)

    admin = data["administracao"]
    assert admin["Nome"] == "MODAL DTVM LTDA"
    assert admin["CNPJ do Fundo"] == "35.765.826/0001-26"
    assert admin["CNPJ do Administrador"] == "36.864.992/0001-42"
    assert admin["Telefone"] == "(11) 3509-0600"
    assert admin["E-mail"] == "infolegal@apexgroup.com"
    assert admin["Site"] == "www.apexgroup.com/apex-brazil/"
    assert admin["Tx administração sobre o PL"] == "0,91%"
    assert admin["Tx administração sobre o Valor de Mercado"] == "1,46%"

    assert (
        data["politica_remuneracao"]
        == "O Administrador fará jus a uma taxa anual equivalente de até 0,75%."
    )


def test_format_fii_administrator_json() -> None:
    data = parse_fii_administrator(FII_ADMIN_HTML)
    json_str = format_fii_administrator_json(data)
    loaded = json.loads(json_str)

    assert loaded["administracao"]["Nome"] == "MODAL DTVM LTDA"
    assert (
        loaded["politica_remuneracao"]
        == "O Administrador fará jus a uma taxa anual equivalente de até 0,75%."
    )


def test_parse_fii_administrator_empty() -> None:
    data = parse_fii_administrator("<div>Sem tabela</div>")
    assert data == {"administracao": {}, "politica_remuneracao": ""}
    assert json.loads(format_fii_administrator_json(data)) == {
        "administracao": {},
        "politica_remuneracao": "",
    }


@pytest.mark.asyncio
async def test_fii_administrator_scraper_fetch() -> None:
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=FII_ADMIN_HTML)
    page.close = AsyncMock()

    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)

    scraper = FIIAdministratorScraper(browser_context, timeout_ms=5000)
    result = await scraper.fetch("aiec11")

    page.goto.assert_awaited_once_with(
        "https://www.fundamentus.com.br/fii_administrador.php?papel=AIEC11",
        wait_until="domcontentloaded",
    )
    page.close.assert_awaited_once()

    loaded = json.loads(result)
    assert loaded["administracao"]["Nome"] == "MODAL DTVM LTDA"
