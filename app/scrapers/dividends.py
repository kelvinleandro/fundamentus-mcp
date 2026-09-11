from urllib.parse import quote

from bs4 import BeautifulSoup, Tag
from playwright.async_api import BrowserContext

from app.models import CompanyDividend, FIIIncome

COMPANY_DIVIDENDS_URL = (
    "https://www.fundamentus.com.br/proventos.php?papel={}&tipo=2"
)
FII_INCOME_URL = "https://www.fundamentus.com.br/fii_proventos.php?papel={}&tipo=2"


def _clean_text(element: Tag) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def parse_company_dividends(html: str) -> list[CompanyDividend]:
    """Parse dividends and interest on equity (JCP) rows from proventos.php."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="resultado")
    if table is None:
        return []

    dividends: list[CompanyDividend] = []
    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        date = _clean_text(cells[0])
        value = _clean_text(cells[1])
        payout_type = _clean_text(cells[2])
        payment_date = _clean_text(cells[3])
        share_count = _clean_text(cells[4])

        if date and value:
            dividends.append(
                {
                    "date": date,
                    "value": value,
                    "type": payout_type,
                    "payment_date": payment_date,
                    "share_count": share_count,
                }
            )

    return dividends


def format_company_dividends(
    dividends: list[CompanyDividend],
    last_n: int | None = None,
) -> str:
    """Format company dividends according to the requested text structure."""
    if not dividends:
        return "Nenhum provento encontrado para o papel pesquisado."

    if last_n is not None and last_n > 0:
        dividends = dividends[:last_n]

    lines = [
        "PROVENTOS",
        "Data - Valor - Tipo - Data de Pagamento - Por quantas ações",
    ]
    for d in dividends:
        lines.append(
            f"{d['date']} - {d['value']} - {d['type']} - {d['payment_date']} - {d['share_count']}"
        )

    return "\n".join(lines)


def parse_fii_income(html: str) -> list[FIIIncome]:
    """Parse income distribution (rendimentos) rows from fii_proventos.php."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="resultado")
    if table is None:
        return []

    incomes: list[FIIIncome] = []
    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        last_date_with = _clean_text(cells[0])
        income_type = _clean_text(cells[1])
        payment_date = _clean_text(cells[2])
        value = _clean_text(cells[3])

        if last_date_with and value:
            incomes.append(
                {
                    "last_date_with": last_date_with,
                    "type": income_type,
                    "payment_date": payment_date,
                    "value": value,
                }
            )

    return incomes


def format_fii_income(
    incomes: list[FIIIncome],
    last_n: int | None = None,
) -> str:
    """Format FII income distributions according to the requested text structure."""
    if not incomes:
        return "Nenhum provento encontrado para o papel pesquisado."

    if last_n is not None and last_n > 0:
        incomes = incomes[:last_n]

    lines = [
        "PROVENTOS",
        "Última Data Com - Tipo - Data de Pagamento - Valor",
    ]
    for inc in incomes:
        lines.append(
            f"{inc['last_date_with']} - {inc['type']} - {inc['payment_date']} - {inc['value']}"
        )

    return "\n".join(lines)


class CompanyDividendsScraper:
    """Scrape and parse historical dividends and JCP for a company on Fundamentus."""

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def fetch(self, ticker: str, last_n: int | None = None) -> str:
        clean_ticker = ticker.strip().upper()
        url = COMPANY_DIVIDENDS_URL.format(quote(clean_ticker, safe=""))
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            return format_company_dividends(
                parse_company_dividends(html),
                last_n=last_n,
            )
        finally:
            await page.close()


class FIIIncomeScraper:
    """Scrape and parse historical income distributions for a FII on Fundamentus."""

    def __init__(self, browser_context: BrowserContext, timeout_ms: float) -> None:
        self._browser_context = browser_context
        self._timeout_ms = timeout_ms

    async def fetch(self, ticker: str, last_n: int | None = None) -> str:
        clean_ticker = ticker.strip().upper()
        url = FII_INCOME_URL.format(quote(clean_ticker, safe=""))
        page = await self._browser_context.new_page()
        page.set_default_navigation_timeout(self._timeout_ms)

        try:
            await page.goto(url, wait_until="domcontentloaded")
            html = await page.content()
            return format_fii_income(
                parse_fii_income(html),
                last_n=last_n,
            )
        finally:
            await page.close()
