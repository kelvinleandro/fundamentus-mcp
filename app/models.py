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


class CompanyDividend(TypedDict):
    date: str
    value: str
    type: str
    payment_date: str
    share_count: str


class FIIIncome(TypedDict):
    last_date_with: str
    type: str
    payment_date: str
    value: str


class FIIPropertyDetail(TypedDict):
    imovel: str
    endereco: str
    area: str
    num_unidades: str
    caracteristicas: str
    taxa_ocupacao: str
    inadimplencia: str
    participacao_receitas: str


AdvancedSearchValue = str | int | float | bool | None
AdvancedSearchFilters = dict[str, AdvancedSearchValue]
