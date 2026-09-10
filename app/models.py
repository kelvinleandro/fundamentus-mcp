from typing import TypedDict

from playwright.async_api import Browser, BrowserContext


class BrowserResources(TypedDict):
    browser: Browser
    browser_context: BrowserContext
    owns_browser_context: bool


class RelevantFact(TypedDict):
    date: str
    company: str
    description: str
    download_url: str
    analysis: str


class PropertyListing(TypedDict):
    fund: str
    property_name: str
    address: str
    other_characteristics: str


class SecurityMatch(TypedDict):
    ticker: str
    commercial_name: str
    legal_name: str


class Shareholder(TypedDict):
    name: str
    percentage: str


class ShareholderCategory(TypedDict):
    category: str
    shareholders: list[Shareholder]


AdvancedSearchValue = str | int | float | bool | None
AdvancedSearchFilters = dict[str, AdvancedSearchValue]
