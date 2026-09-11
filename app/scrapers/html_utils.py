from collections.abc import Mapping

from bs4 import Tag


def normalize_header(value: str) -> str:
    return " ".join(value.casefold().split())


def find_column(headers: Mapping[str, int], *names: str) -> int:
    for name in names:
        normalized_name = normalize_header(name)
        if normalized_name in headers:
            return headers[normalized_name]
    raise ValueError(f"Missing required table column: {', '.join(names)}")


def cell_text(cell: Tag) -> str:
    return " ".join(cell.get_text(" ", strip=True).split())


def link_text(cell: Tag) -> str:
    link = cell.find("a")
    if link is None:
        return ""
    return " ".join(link.get_text(" ", strip=True).split())


def link_href(cell: Tag) -> str:
    link = cell.find("a", href=True)
    if link is None:
        return ""
    return link["href"]
