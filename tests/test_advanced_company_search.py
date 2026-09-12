import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.advanced_company_search import (
    AdvancedCompanySearchScraper,
    count_result_rows,
    parse_company_search_results,
    validate_advanced_filters,
)


RESULT_HTML = """
<table id="resultado">
  <thead>
    <tr><th>Papel</th><th>Cotação</th><th>P/L</th></tr>
  </thead>
  <tbody>
    <tr><td><a href="detalhes.php?papel=PETR4">PETR4</a></td><td>38,50</td><td>4,20</td></tr>
    <tr><td><a href="detalhes.php?papel=VALE3">VALE3</a></td><td>60,10</td><td>5,80</td></tr>
  </tbody>
</table>
"""


def test_count_result_rows_ignores_header() -> None:
    assert count_result_rows(RESULT_HTML) == 2


def test_parse_company_search_results() -> None:
    results = parse_company_search_results(RESULT_HTML)
    assert len(results) == 2
    assert results[0] == {
        "Papel": "PETR4",
        "Cotação": "38,50",
        "P/L": "4,20",
    }
    assert results[1]["Papel"] == "VALE3"


def test_validate_advanced_filters_accepts_form_fields() -> None:
    validate_advanced_filters(
        {
            "pl_min": 1.5,
            "setor": "20",
            "negociada": True,
        }
    )


def test_validate_advanced_filters_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError, match="Unknown advanced search field"):
        validate_advanced_filters({"unknown_field": "value"})


@pytest.mark.asyncio
async def test_search_fills_fields_and_returns_result_json() -> None:
    page = MagicMock()
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value=RESULT_HTML)
    page.close = AsyncMock()
    page.set_default_navigation_timeout = MagicMock()
    # Single evaluate call builds and submits the hidden form
    page.evaluate = AsyncMock()
    page.wait_for_url = AsyncMock()

    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=page)
    scraper = AdvancedCompanySearchScraper(browser_context, timeout_ms=30_000)

    result = await scraper.search(
        {"pl_min": 1.5, "setor": "20", "negociada": False}
    )

    data = json.loads(result)
    assert len(data) == 2
    assert data[0]["Papel"] == "PETR4"
    assert data[0]["Cotação"] == "38,50"

    # evaluate is called once with (js_string, [form_name, overrides_dict])
    page.evaluate.assert_awaited_once()
    call_args = page.evaluate.call_args
    form_name, payload = call_args.args[1]  # [formName, overrides]
    assert form_name == "formbusca"
    assert payload["setor"] == "20"
    assert payload["pl_min"] == 1.5
    # negociada=False is passed to JS which removes it from params (unchecked = not sent)
    assert payload["negociada"] is False

    page.wait_for_url.assert_awaited_once()
    page.close.assert_awaited_once()
