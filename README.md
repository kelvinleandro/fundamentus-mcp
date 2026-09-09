This project uses uv, FastMCP, and Playwright with the Obscura headless browser
over its Chrome DevTools Protocol (CDP) endpoint.

## Run

Install the dependencies and start the MCP server with:

```powershell
uv sync
$env:OBSCURA_CDP_URL = "http://127.0.0.1:9222"
uv run main.py
```

The server connects to Obscura once when the MCP server starts and keeps the
connection open for its entire lifespan. It reuses Obscura's existing browser
context when one is available. The `fetch_page` tool navigates using that
context and returns the page title. Add future scraping tools by getting the
shared context from `ctx.lifespan_context["browser_context"]`.
