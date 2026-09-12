from collections.abc import Mapping
import json

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext

SELECT_FIELDS = {"setor", "ordem"}
CHECKBOX_FIELDS = {"negociada", "ult_balanco_entregue"}


def count_result_rows(html: str) -> int:
    """Count data rows in the advanced company search result table."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="resultado")
    if table is None:
        raise ValueError("Table with id 'resultado' was not found")
    return sum(1 for row in table.find_all("tr") if row.find("td") is not None)


def parse_company_search_results(html: str) -> list[dict[str, str]]:
    """Parse company rows from the advanced search result table into dictionaries."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="resultado")
    if table is None:
        return []

    thead = table.find("thead")
    headers: list[str] = []
    if thead:
        header_row = thead.find("tr")
        if header_row:
            headers = [
                " ".join(th.get_text(" ", strip=True).split())
                for th in header_row.find_all(["th", "td"])
            ]

    results: list[dict[str, str]] = []
    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        row_data: dict[str, str] = {}
        for index, cell in enumerate(cells):
            header = headers[index] if index < len(headers) else f"col_{index}"
            row_data[header] = " ".join(cell.get_text(" ", strip=True).split())

        if row_data:
            results.append(row_data)

    return results


def validate_advanced_filters(filters: Mapping[str, object]) -> None:
    """Reject unknown form fields before interacting with the live page."""
    allowed_fields = {
        "pl_min",
        "pl_max",
        "pvp_min",
        "pvp_max",
        "psr_min",
        "psr_max",
        "divy_min",
        "divy_max",
        "pativos_min",
        "pativos_max",
        "pcapgiro_min",
        "pcapgiro_max",
        "pebit_min",
        "pebit_max",
        "fgrah_min",
        "fgrah_max",
        "firma_ebit_min",
        "firma_ebit_max",
        "firma_ebitda_min",
        "firma_ebitda_max",
        "margemebit_min",
        "margemebit_max",
        "margemliq_min",
        "margemliq_max",
        "liqcorr_min",
        "liqcorr_max",
        "roic_min",
        "roic_max",
        "roe_min",
        "roe_max",
        "liq_min",
        "liq_max",
        "patrim_min",
        "patrim_max",
        "divliquida_min",
        "divliquida_max",
        "tx_cresc_rec_min",
        "tx_cresc_rec_max",
        "setor",
        "negociada",
        "ult_balanco_entregue",
        "ordem",
    }
    unknown_fields = set(filters) - allowed_fields
    if unknown_fields:
        names = ", ".join(sorted(unknown_fields))
        raise ValueError(f"Unknown advanced search field(s): {names}")


class AdvancedCompanySearchScraper:
    """Submit Fundamentus's advanced company search form."""

    SEARCH_FORM_URL = "https://www.fundamentus.com.br/buscaavancada.php"
    RESULT_URL_PATTERN = "**/resultado.php"
    FORM_NAME = "formbusca"

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def search(self, filters: Mapping[str, object]) -> str:
        validate_advanced_filters(filters)
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(self.SEARCH_FORM_URL, wait_until="domcontentloaded")

            # Build the form payload by reading current defaults from the page,
            # then merging in the user filters. This avoids CDP select_option
            # bugs and the page's JS overriding programmatic DOM changes.
            # The evaluate may raise "Execution context was destroyed" when hidden.submit()
            # navigates the page before evaluate() returns — this is expected and safe.
            try:
                await page.evaluate(
                    """([formName, overrides]) => {
                        const form = document.querySelector('form[name="' + formName + '"]');
                        // Collect current form values as defaults
                        const params = new URLSearchParams(new FormData(form));
                        // Apply user overrides
                        for (const [key, value] of Object.entries(overrides)) {
                            if (value === null || value === undefined) {
                                params.delete(key);
                            } else if (value === false || value === 'false') {
                                // Unchecked checkbox: remove from params so it is not sent
                                params.delete(key);
                            } else {
                                params.set(key, String(value));
                            }
                        }
                        // Create a hidden form and submit it
                        const hidden = document.createElement('form');
                        hidden.method = 'POST';
                        hidden.action = form.action;
                        for (const [key, value] of params.entries()) {
                            const input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = key;
                            input.value = value;
                            hidden.appendChild(input);
                        }
                        document.body.appendChild(hidden);
                        hidden.submit();
                    }""",
                    [self.FORM_NAME, {k: v for k, v in filters.items() if v is not None}],
                )
            except Exception as exc:
                if "Execution context was destroyed" not in str(exc):
                    raise
            await page.wait_for_url(
                self.RESULT_URL_PATTERN,
                wait_until="domcontentloaded",
                timeout=self._timeout_ms,
            )

            html = await page.content()
            return json.dumps(
                parse_company_search_results(html),
                ensure_ascii=False,
                indent=2,
            )
        finally:
            await page.close()