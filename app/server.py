from fastmcp import FastMCP

from app.config import Settings
from app.lifespan import browser_lifespan
from app.tools.page_tools import register_page_tools


def create_server(settings: Settings) -> FastMCP:
    """Create and configure the application MCP server."""
    mcp = FastMCP("Fundamentus MCP", lifespan=browser_lifespan)
    register_page_tools(mcp, settings)
    return mcp
