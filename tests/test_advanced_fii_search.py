from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scrapers.advanced_fii_search import (
    AdvancedFIISearchScraper,
    count_result_rows,
    validate_fii_filters,
)


RESULT_HTML = """
<table id="tabelaResultado">
  <tr><th>Papel</th><th>Segmento</th></tr>
  <tr><td><a href="fii_detalhes.php?papel=KNRI11">KNRI11</a></td><td>Logística</td></tr>
  <tr><td><a href="fii_detalhes.php?papel=HGLG11">HGLG11</a></td><td>Logística</td></tr>
</table>
"""


def test_count_result_rows_ignores_header() -> None:
    assert count_result_rows(RESULT_HTML) == 2


def test_count_result_rows_raises_when_table_missing() -> None:
    with pytest.raises(ValueError, match="tabelaResultado"):
        count_result_rows("<html><body>no table</body></html>")


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
async def test_search_submits_form_and_returns_row_count() -> None:
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

    assert result == "2"

    page.evaluate.assert_awaited_once()
    call_args = page.evaluate.call_args
    form_name, payload = call_args.args[1]
    assert form_name == "formbusca"
    assert payload["divy_min"] == 0.08
    assert payload["segmento"] == "6"
    assert payload["negociada"] is False

    page.wait_for_url.assert_awaited_once()
    page.close.assert_awaited_once()
