from collections.abc import Mapping
import json

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext

SELECT_FIELDS = {"segmento"}
CHECKBOX_FIELDS = {"negociada"}


def count_result_rows(html: str) -> int:
    """Count data rows in the FII advanced search result table."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tabelaResultado")
    if table is None:
        raise ValueError("Table with id 'tabelaResultado' was not found")
    return sum(1 for row in table.find_all("tr") if row.find("td") is not None)


def parse_fii_search_results(html: str) -> list[dict[str, str]]:
    """Parse FII rows from the advanced search result table into dictionaries."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tabelaResultado") or soup.find("table", id="resultado")
    if table is None:
        return []

    thead = table.find("thead")
    headers: list[str] = []
    valid_indices: list[int] = []
    if thead:
        header_row = thead.find("tr")
        if header_row:
            raw_ths = header_row.find_all(["th", "td"])
            for idx, th in enumerate(raw_ths):
                name = " ".join(th.get_text(" ", strip=True).split())
                style = th.get("style", "").lower()
                # Omit hidden columns like Endereço which are not visually displayed
                if "display: none" in style or "display:none" in style or name.lower() == "endereço":
                    continue
                valid_indices.append(idx)
                headers.append(name)

    results: list[dict[str, str]] = []
    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        row_data: dict[str, str] = {}
        if valid_indices and len(valid_indices) == len(headers):
            for header, idx in zip(headers, valid_indices):
                if idx < len(cells):
                    row_data[header] = " ".join(cells[idx].get_text(" ", strip=True).split())
        else:
            for index, cell in enumerate(cells):
                header = headers[index] if index < len(headers) else f"col_{index}"
                if header.lower() == "endereço":
                    continue
                row_data[header] = " ".join(cell.get_text(" ", strip=True).split())

        if row_data:
            results.append(row_data)

    return results


def validate_fii_filters(filters: Mapping[str, object]) -> None:
    """Reject unknown form fields before interacting with the live page."""
    allowed_fields = {
        "ffo_y_min",
        "ffo_y_max",
        "divy_min",
        "divy_max",
        "pvp_min",
        "pvp_max",
        "mk_cap_min",
        "mk_cap_max",
        "qtd_imoveis_min",
        "qtd_imoveis_max",
        "preco_m2_min",
        "preco_m2_max",
        "aluguel_m2_min",
        "aluguel_m2_max",
        "cap_rate_min",
        "cap_rate_max",
        "vacancia_min",
        "vacancia_max",
        "segmento",
        "negociada",
    }
    unknown_fields = set(filters) - allowed_fields
    if unknown_fields:
        names = ", ".join(sorted(unknown_fields))
        raise ValueError(f"Unknown FII search field(s): {names}")


class AdvancedFIISearchScraper:
    """Submit Fundamentus's advanced FII search form."""

    SEARCH_FORM_URL = "https://www.fundamentus.com.br/fii_buscaavancada.php"
    RESULT_URL_PATTERN = "**/fii_resultado.php"
    FORM_NAME = "formbusca"

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def search(self, filters: Mapping[str, object]) -> str:
        validate_fii_filters(filters)
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
                parse_fii_search_results(html),
                ensure_ascii=False,
                indent=2,
            )
        finally:
            await page.close()
