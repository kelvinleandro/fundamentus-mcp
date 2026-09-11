import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.fii_properties import (
    FIIPropertiesScraper,
    format_fii_properties_json,
    parse_fii_properties,
)

FII_PROPERTIES_HTML = """
<table id="resultado" class="resultado rowstyle-par colstyle-col no-arrow" border="0" cellpadding="0" cellspacing="0">
  <thead>
    <tr>
      <th><a href="#">Imóvel</a></th>
      <th><a href="#">Endereço</a></th>
      <th><a href="#">Área</a></th>
      <th><a href="#">Num Unidades</a></th>
      <th><a href="#">Características</a></th>
      <th><a href="#">% tx ocupação</a></th>
      <th><a href="#">% inadimplência</a></th>
      <th><a href="#">% das receitas do fii</a></th>
    </tr>
  </thead>
  <tbody>
    <tr class="">
      <td>Grand Plaza Shopping</td>
      <td><a target="_blank" href="https://maps.google.com">Avenida Industrial, 600, Centro, Santo André - SP</a></td>
      <td>69.812</td>
      <td>286</td>
      <td>Shopping Center</td>
      <td style="text-align: right;">98,50% <a href="#" onclick="obtemGraficoOcupacao(1);return false;"><img src="img/chart.svg" alt="Gráfico"></a></td>
      <td>1,91%</td>
      <td>97,94%</td>
    </tr>
  </tbody>
</table>
"""


def test_parse_fii_properties() -> None:
    properties = parse_fii_properties(FII_PROPERTIES_HTML)
    assert len(properties) == 1
    prop = properties[0]
    assert prop["imovel"] == "Grand Plaza Shopping"
    assert prop["endereco"] == "Avenida Industrial, 600, Centro, Santo André - SP"
    assert prop["area"] == "69.812"
    assert prop["num_unidades"] == "286"
    assert prop["caracteristicas"] == "Shopping Center"
    assert prop["taxa_ocupacao"] == "98,50%"
    assert prop["inadimplencia"] == "1,91%"
    assert prop["participacao_receitas"] == "97,94%"


def test_format_fii_properties_json() -> None:
    properties = parse_fii_properties(FII_PROPERTIES_HTML)
    json_str = format_fii_properties_json(properties)
    data = json.loads(json_str)

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["imovel"] == "Grand Plaza Shopping"
    assert data[0]["taxa_ocupacao"] == "98,50%"


def test_parse_fii_properties_empty() -> None:
    assert parse_fii_properties("<div>Sem tabela</div>") == []
    assert format_fii_properties_json([]) == "[]"


@pytest.mark.asyncio
async def test_fii_properties_scraper_fetch() -> None:
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=FII_PROPERTIES_HTML)
    page.close = AsyncMock()

    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)

    scraper = FIIPropertiesScraper(browser_context, timeout_ms=5000)
    result = await scraper.fetch("aiec11")

    page.goto.assert_awaited_once_with(
        "https://www.fundamentus.com.br/fii_imoveis_detalhes.php?papel=AIEC11",
        wait_until="domcontentloaded",
    )
    page.close.assert_awaited_once()

    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["imovel"] == "Grand Plaza Shopping"
