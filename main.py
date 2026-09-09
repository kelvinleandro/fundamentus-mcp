from app.config import load_settings
from app.server import create_server


def main() -> None:
    """Create and run the Fundamentus MCP server."""
    server = create_server(load_settings())
    server.run()


if __name__ == "__main__":
    main()