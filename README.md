# Fundamentus MCP Server

A production-ready [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server providing tools to scrape, search, and analyze Brazilian financial market data (B3 stocks and FIIs) from [Fundamentus](https://www.fundamentus.com.br/).

Built with **Python 3.12+**, **FastMCP**, **Playwright**, and designed to connect to the [**Obscura**](https://obscura.sh/) headless browser (or any Chromium-based browser with CDP enabled).

---

## Features & Tools

The server exposes the following MCP tools:

- `search_companies_advanced`: Advanced fundamental screening for B3 stocks with multi-criteria filters:
  - Valuation & Multiples: P/L (`pl_min`/`pl_max`), P/VP (`pvp_min`/`pvp_max`), PSR, EV/EBIT, EV/EBITDA, P/Ativos.
  - Returns & Margins: Dividend Yield (`divy`), ROIC, ROE, EBIT Margin, Net Margin.
  - Health & Liquidity: Current Liquidity (`liqcorr`), Net Debt / Equity (`divliquida`), Net Equity (`patrim`).
  - Sector & Status: Sector filter (`setor`), share liquidity, traded in the last 2 months (`negociada`), latest balance sheet submitted (`ult_balanco_entregue`).
- `search_fii_advanced`: Advanced fundamental screening for Real Estate Investment Trusts (FIIs):
  - Metrics: Dividend Yield (`divy`), P/VP (`pvp`), FFO Yield (`ffo_y`), Cap Rate (`cap_rate`), Vacancy Rate (`vacancia`), Market Cap (`mk_cap`), Price/m², Rent/m², Number of properties.
  - Categorization: Real estate segment (`segmento` - Logistics, Shopping, Corporate, etc.) and traded status (`negociada`).
- `search_security`: Search companies, stocks, or FIIs by ticker symbol or partial name.
- `search_properties`: Search physical properties held by FIIs with optional text query.
- `get_relevant_facts`: Retrieve the latest relevant facts (*fatos relevantes*) with PDF report links.
- `fetch_example_page`: Helper tool to fetch the title of an example page (verifies browser connectivity).

---

## Requirements

- Python `>=3.12`
- [`uv`](https://docs.astral.sh/uv/) for package and dependency management
- Obscura headless browser (or a Chromium instance with Chrome DevTools Protocol enabled)

---

## Configuration

Copy the `.env.example` file to `.env` and adjust the configuration if needed:

```bash
cp .env.example .env
```

*(On Windows PowerShell: `Copy-Item .env.example .env`)*

The application automatically loads variables from `.env` via `python-dotenv`.

| Variable | Description | Required | Example |
|---|---|:---:|---|
| `OBSCURA_CDP_URL` | Endpoint URL for the browser's CDP interface | Yes | `ws://127.0.0.1:9222/devtools/browser` |

---

## Installation & Running

1. **Install dependencies:**

   ```bash
   uv sync
   ```

2. **Configure environment:**

   Create your `.env` file from `.env.example` as shown above.

3. **Start the MCP server:**

   ```bash
   uv run main.py
   ```

### Testing with MCP Inspector

You can test and inspect the tools interactively in your browser using the official [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector uv run main.py
```

### MCP Client Integration (e.g., Claude Desktop, Cursor, Antigravity)

Add this server configuration to your MCP settings file:

```json
{
  "mcpServers": {
    "fundamentus": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/fundamentus-mcp",
        "main.py"
      ]
    }
  }
}
```

---

## Architecture & Lifespan

- **Single CDP Connection**: Connects to the browser over CDP once during MCP server startup (`browser_lifespan`) and cleanly releases resources upon shutdown.
- **Context Reuse**: Reuses Obscura's existing browser context when available, creating isolated per-operation pages to prevent memory leaks and state pollution.
- **Resilient Navigation & Parsing**: Input validation on search filters, normalized number formats (`.` as decimal separator), and robust HTML parsing with BeautifulSoup.

---

## Testing

Run unit tests without needing an active browser:

```powershell
uv run pytest tests/ -v
```
