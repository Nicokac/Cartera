"""Clientes para fuentes externas del proyecto."""

from .bonistas_client import (
    get_bonds_for_portfolio,
    get_instrument_data,
    get_listing,
    get_macro_variables,
    normalize_bonistas_ticker,
)
from .bcra import get_rem_latest

__all__ = [
    "get_rem_latest",
    "get_bonds_for_portfolio",
    "get_instrument_data",
    "get_listing",
    "get_macro_variables",
    "normalize_bonistas_ticker",
]
