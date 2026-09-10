from typing import cast

from fastmcp import Context, FastMCP

from app.config import Settings
from app.models import AdvancedSearchFilters, BrowserResources
from app.scrapers.page_scraper import PageScraper
from app.scrapers.relevant_facts import RelevantFactsScraper
from app.scrapers.properties import PropertyScraper
from app.scrapers.security_search import SecuritySearchScraper
from app.scrapers.major_shareholders import MajorShareholdersScraper
from app.scrapers.advanced_company_search import AdvancedCompanySearchScraper
from app.scrapers.advanced_fii_search import AdvancedFIISearchScraper


def register_page_tools(mcp: FastMCP, settings: Settings) -> None:
    """Register page scraping tools on the MCP server."""

    @mcp.tool
    async def fetch_example_page(ctx: Context) -> str:
        """Perform a browser health check by fetching an example page title.

        Navigates to example.com using the shared Playwright CDP browser context
        and returns the document title. Use this diagnostic tool to verify that
        the CDP connection to Obscura/Chromium is healthy and responsive before
        running deeper scraping tasks. Does not return financial data.
        """
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = PageScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.fetch_example_title()

    @mcp.tool
    async def get_relevant_facts(ctx: Context) -> str:
        """Fetch the latest corporate relevant facts (Fatos Relevantes) from Fundamentus.

        Retrieves recent official material disclosures and notices (FR) released
        by publicly traded companies on B3.

        Returns:
            A formatted text block of announcements separated by '----'. Each entry
            contains:
            - Publication date, company name, and classification/ticker reference.
            - Headline description of the material fact (e.g., dividends declaration,
              M&A, quarterly earnings notice, restructuring).
            - Direct download link to the original official PDF disclosure.

        Best used when the user asks about recent corporate events, news, or regulatory
        filings for Brazilian companies.
        """
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = PageScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await RelevantFactsScraper(scraper).fetch()

    @mcp.tool
    async def search_properties(
        ctx: Context,
        text: str | None = None,
    ) -> str:
        """Search physical real estate properties held by Brazilian REITs (FIIs).

        Queries the Fundamentus property catalog (fii_imoveis.php) for physical
        assets owned by Real Estate Investment Trusts (Fundos de Tijolo).

        Parameters:
            text: Optional search query to filter properties. Can be:
                - A FII ticker symbol (e.g., "HGLG11", "KNRI11", "XPLG11").
                - A location, city, or state (e.g., "São Paulo", "SP", "Curitiba").
                - A property name or asset type (e.g., "Galpão", "Centro Logístico", "Torre").
                If omitted, returns the full catalog of available properties.

        Returns:
            A formatted text block of matching properties separated by '----'. Each entry
            includes:
            - FII ticker and property name.
            - Full street address, city, and state.
            - Additional characteristics (e.g., gross leasable area / ABL, number of units,
              vacancy, or specialized infrastructure notes) when available.
        """
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = PropertyScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.search(text)

    @mcp.tool
    async def search_security(ctx: Context, term: str) -> str:
        """Search for a Brazilian stock (company) or Real Estate Investment Trust (FII).

        This is the primary tool for detailed asset profiles. It navigates to
        Fundamentus's security details page (detalhes.php?papel=...) for the given term.

        Behavior and return types:

        1. Exact ticker match (e.g., "PETR4", "VALE3", "ITUB4", "HGLG11", "MXRF11"):
           Navigates directly to the asset's page and returns a comprehensive, structured
           JSON object with all fundamentals:

           - For Companies / Stocks:
             * "geral": Ticker, price, company name, sector, subsector, market cap,
               firm value (EV), share count, and recent daily volume.
             * "oscilacoes": Historical returns (Day, Month, 30 days, 12 months, and
               prior calendar years).
             * "indicadores_fundamentalistas": Key valuation and performance multiples:
               P/L, P/VP, PSR, Dividend Yield, EV/EBIT, EV/EBITDA, ROE, ROIC, Margem
               Bruta, Margem EBIT, Margem Líquida, Liquidez Corrente, Dív. Bruta/PL,
               Giro Ativos, and 5-year revenue growth.
             * "dados_balanco_patrimonial": Assets, cash/equivalents, gross debt, net
               debt, and shareholders' equity.
             * "dados_demonst_resultados": DRE segregated into "ultimos_12_meses" and
               "ultimos_3_meses" (Net Revenue, EBIT, and Net Income).

           - For FIIs (Real Estate Investment Trusts):
             * "geral": FII ticker, quotation, fund name, mandate, segment, market cap,
               and number of quotas.
             * "oscilacoes": Return performance over day and month.
             * "indicadores": FII multiples such as P/VP, FFO Yield, and Dividend Yield.
             * "resultado": Revenue segregated into 12M and 3M.
             * "balanco_patrimonial": Total assets and net worth.
             * "imoveis": Portfolio metrics including number of properties, total area
               in m² (ABL), and cap rate.

        2. Ambiguous or partial name (e.g., "Petrobras", "Itau", "Logistica"):
           Returns a formatted list of matching candidates with their tickers, commercial
           names, and legal company names. Inspect the list and call `search_security`
           again using the chosen specific ticker to retrieve the full JSON dataset.

        Parameters:
            term: Ticker symbol (preferred, e.g., "PETR4", "HGLG11") or search keyword
                  (e.g., "Banco do Brasil").
        """
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = SecuritySearchScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.search(term)

    @mcp.tool
    async def get_major_shareholders(ctx: Context, ticker: str) -> str:
        """Retrieve the major shareholders (principais acionistas) and their equity stakes.

        Queries Fundamentus (principais_acionistas.php?papel=...) to obtain the
        controlling groups, institutional investors, and substantial shareholding
        breakdown for a Brazilian publicly traded company.

        Parameters:
            ticker: The stock ticker symbol of the company (e.g., "SANB3", "PETR4", "VALE3", "ITUB4").

        Returns:
            A formatted text block organized by share class (e.g., AÇÕES ORDINÁRIAS,
            AÇÕES PREFERENCIAIS, CAPITAL TOTAL). Each section lists:
            Acionista - Participação
            {Nome do Acionista} - {Percentual}%
        """
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = MajorShareholdersScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.fetch(ticker)

    @mcp.tool
    async def search_companies_advanced(
        ctx: Context,
        filters: AdvancedSearchFilters,
    ) -> str:
        """Search companies using Fundamentus's advanced financial filters.

        Call this tool with one `filters` object, for example:

        ```json
        {"filters": {"setor": "34", "negociada": true}}
        ```

        The `filters` dictionary may contain any combination of the following
        fields. Omitted fields are left empty and therefore do not constrain
        the search. Numeric values must use decimal notation, not percentages:
        use `0.15` for 15%.

        Range filters accept `*_min` and `*_max` string or numeric values:

        - `pl_min`, `pl_max`: price-to-earnings ratio (P/L).
        - `pvp_min`, `pvp_max`: price-to-book ratio (P/VP).
        - `psr_min`, `psr_max`: price-to-sales ratio (PSR).
        - `divy_min`, `divy_max`: dividend yield as a decimal.
        - `pativos_min`, `pativos_max`: price-to-assets ratio.
        - `pcapgiro_min`, `pcapgiro_max`: price-to-working-capital ratio.
        - `pebit_min`, `pebit_max`: price-to-EBIT ratio.
        - `fgrah_min`, `fgrah_max`: price-to-net-current-assets ratio.
        - `firma_ebit_min`, `firma_ebit_max`: EV/EBIT ratio.
        - `firma_ebitda_min`, `firma_ebitda_max`: EV/EBITDA ratio.
        - `margemebit_min`, `margemebit_max`: EBIT margin as a decimal.
        - `margemliq_min`, `margemliq_max`: net margin as a decimal.
        - `liqcorr_min`, `liqcorr_max`: current liquidity ratio.
        - `roic_min`, `roic_max`: return on invested capital as a decimal.
        - `roe_min`, `roe_max`: return on equity as a decimal.
        - `liq_min`, `liq_max`: share liquidity.
        - `patrim_min`, `patrim_max`: shareholders' equity.
        - `divliquida_min`, `divliquida_max`: net debt divided by equity.
        - `tx_cresc_rec_min`, `tx_cresc_rec_max`: five-year revenue growth
            rate as a decimal.

        Select fields:

        - `setor`: sector code as a string. Valid values are:
            `"1"` Agropecuária, `"2"` Água e Saneamento, `"3"` Alimentos
            Processados, `"5"` Automóveis e Motocicletas, `"6"` Bebidas,
            `"7"` Comércio, `"8"` Comércio e Distribuição, `"9"`
            Computadores e Equipamentos, `"10"` Construção Civil, `"11"`
            Construção e Engenharia, `"12"` Diversos, `"13"` Embalagens,
            `"14"` Energia Elétrica, `"15"` Equipamentos, `"16"` Exploração
            de Imóveis, `"17"` Gás, `"18"` Holdings Diversificadas, `"19"`
            Hotéis e Restaurantes, `"20"` Intermediários Financeiros, `"21"`
            Madeira e Papel, `"22"` Máquinas e Equipamentos, `"23"` Materiais
            Diversos, `"24"` Material de Transporte, `"25"` Medicamentos e
            Outros Produtos, `"26"` Mídia, `"27"` Mineração, `"28"` Outros,
            `"29"` Outros Títulos, `"30"` Petróleo, Gás e Biocombustíveis,
            `"31"` Previdência e Seguros, `"32"` Produtos de Uso Pessoal e de
            Limpeza, `"33"` Programas e Serviços, `"34"` Químicos, `"35"`
            Securitizadoras de Recebíveis, `"4"` Serviços Médicos,
            Hospitalares, Análises e Diagnósticos, `"36"` Serviços Diversos,
            `"37"` Serviços Financeiros Diversos, `"38"` Siderurgia e
            Metalurgia, `"39"` Tecidos, Vestuário e Calçados, `"40"`
            Telecomunicações, `"41"` Transporte, `"42"` Utilidades Domésticas,
            and `"43"` Viagens e Lazer.
        - `ordem`: sort order code as a string. Valid values are:
            `"1"` P/L, `"2"` P/VP, `"3"` PSR, `"4"` Dividend Yield,
            `"5"` P/Ativos, `"6"` P/Cap. Giro, `"7"` P/Ativo Circ. Liq.,
            `"8"` P/EBIT, `"9"` EV/EBIT, `"10"` EV/EBITDA, `"11"` Margem EBIT,
            `"12"` Margem Líquida, `"13"` Liquidez Corrente, `"14"` ROIC,
            `"15"` ROE, `"16"` Liquidez das Ações, `"17"` Patrimônio Líquido,
            `"18"` Dív. Líquida sobre o Patrimônio Líquido, and `"19"` Tx. de
            crescimento da Receita Líq.

        Checkbox fields accept boolean values:

        - `negociada`: require shares traded in the last two months.
        - `ult_balanco_entregue`: require the latest quarterly balance sheet
            to have been published.

        Examples:

        ```python
        {"pl_min": 1, "pl_max": 10, "pvp_max": 2}
        {"divy_min": 0.05, "roic_min": 0.10, "setor": "20"}
        {"negociada": True, "ult_balanco_entregue": True, "ordem": "15"}
        ```

        The return value is the number of companies matching the filters as a
        string. Unknown field names are rejected. The advanced search form
        uses `.` as the decimal separator.
        """
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = AdvancedCompanySearchScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.search(filters)

    @mcp.tool
    async def search_fii_advanced(
        ctx: Context,
        filters: AdvancedSearchFilters,
    ) -> str:
        """Search FIIs using Fundamentus's advanced filter form.

        Call this tool with one `filters` object, for example:

        ```json
        {"filters": {"segmento": "6", "negociada": true}}
        ```

        The `filters` dictionary may contain any combination of the following
        fields. Omitted fields are left empty. Numeric values must use decimal
        notation, not percentages: use `0.10` for 10%.

        Range filters accept `*_min` and `*_max` string or numeric values:

        - `ffo_y_min`, `ffo_y_max`: FFO Yield (Funds From Operation Yield).
        - `divy_min`, `divy_max`: dividend yield as a decimal.
        - `pvp_min`, `pvp_max`: price-to-book ratio (P/VP).
        - `mk_cap_min`, `mk_cap_max`: market cap in BRL.
        - `qtd_imoveis_min`, `qtd_imoveis_max`: number of properties.
        - `preco_m2_min`, `preco_m2_max`: price per square meter.
        - `aluguel_m2_min`, `aluguel_m2_max`: rent per square meter.
        - `cap_rate_min`, `cap_rate_max`: cap rate as a decimal.
        - `vacancia_min`, `vacancia_max`: weighted vacancy rate as a decimal.

        Select fields:

        - `segmento`: segment code as a string. Valid values are:
            `"14"` Educacional, `"12"` Escritórios, `"2"` Híbrido,
            `"3"` Hospital, `"4"` Hotel, `"1"` Indefinido,
            `"5"` Lajes Corporativas, `"6"` Logística, `"11"` Multicategoria,
            `"7"` Outros, `"8"` Residencial, `"9"` Shoppings,
            `"10"` Títulos e Val. Mob., `"13"` Varejo.

        Checkbox fields accept boolean values:

        - `negociada`: require FII shares traded in the last two months.

        Examples:

        ```python
        {"divy_min": 0.08, "pvp_max": 1.0}
        {"segmento": "9", "negociada": True}
        {"cap_rate_min": 0.07, "vacancia_max": 0.10, "segmento": "6"}
        ```

        The return value is the number of FIIs matching the filters as a
        string. Unknown field names are rejected.
        """
        resources = cast(BrowserResources, ctx.lifespan_context)
        scraper = AdvancedFIISearchScraper(
            browser_context=resources["browser_context"],
            timeout_ms=settings.page_navigation_timeout_ms,
        )
        return await scraper.search(filters)
