import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.advanced_fii_search import (
    AdvancedFIISearchScraper,
    count_result_rows,
    parse_fii_search_results,
    validate_fii_filters,
)


RESULT_HTML = """
<table id="tabelaResultado">
  <thead>
    <tr><th>Papel</th><th>Segmento</th><th>Cotação</th></tr>
  </thead>
  <tbody>
    <tr><td><a href="fii_detalhes.php?papel=KNRI11">KNRI11</a></td><td>Logística</td><td>145,00</td></tr>
    <tr><td><a href="fii_detalhes.php?papel=HGLG11">HGLG11</a></td><td>Logística</td><td>160,20</td></tr>
  </tbody>
</table>
"""


def test_count_result_rows_ignores_header() -> None:
    assert count_result_rows(RESULT_HTML) == 2


def test_count_result_rows_raises_when_table_missing() -> None:
    with pytest.raises(ValueError, match="tabelaResultado"):
        count_result_rows("<html><body>no table</body></html>")


def test_parse_fii_search_results() -> None:
    results = parse_fii_search_results(RESULT_HTML)
    assert len(results) == 2
    assert results[0] == {
        "Papel": "KNRI11",
        "Segmento": "Logística",
        "Cotação": "145,00",
    }
    assert results[1]["Papel"] == "HGLG11"


def test_parse_fii_search_results_ignores_hidden_endereco() -> None:
    html_with_hidden_endereco = """
    <table id="tabelaResultado">
      <thead>
        <tr>
          <th>Papel</th>
          <th>Cotação</th>
          <th style="display: none;">Endereço</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><a href="fii_detalhes.php?papel=KNRI11">KNRI11</a></td>
          <td>145,00</td>
          <td style="display:none">Av. Paulista, 1000</td>
        </tr>
      </tbody>
    </table>
    """
    results = parse_fii_search_results(html_with_hidden_endereco)
    assert len(results) == 1
    assert results[0] == {
        "Papel": "KNRI11",
        "Cotação": "145,00",
    }
    assert "Endereço" not in results[0]


def test_validate_fii_filters_accepts_known_fields() -> None:
    validate_fii_filters(
        {
            "divy_min": 0.08,
            "pvp_max": 1.0,
            "segmento": "6",
            "negociada": True,
        }
    )


def test_validate_fii_filters_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError, match="Unknown FII search field"):
        validate_fii_filters({"setor": "1"})  # company field, not FII


@pytest.mark.asyncio
async def test_search_submits_form_and_returns_row_json() -> None:
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=RESULT_HTML)
    page.close = AsyncMock()
    page.set_default_navigation_timeout = MagicMock()
    page.evaluate = AsyncMock()
    page.wait_for_url = AsyncMock()

    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)
    scraper = AdvancedFIISearchScraper(browser_context, timeout_ms=30_000)

    result = await scraper.search({"divy_min": 0.08, "segmento": "6", "negociada": False})

    data = json.loads(result)
    assert len(data) == 2
    assert data[0]["Papel"] == "KNRI11"
    assert data[0]["Cotação"] == "145,00"

    page.evaluate.assert_awaited_once()
    call_args = page.evaluate.call_args
    form_name, payload = call_args.args[1]
    assert form_name == "formbusca"
    assert payload["divy_min"] == 0.08
    assert payload["segmento"] == "6"
    assert payload["negociada"] is False

    page.wait_for_url.assert_awaited_once()
    page.close.assert_awaited_once()
