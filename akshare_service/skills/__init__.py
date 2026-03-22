"""
Skills module - 标准化财务数据接口
"""

from .finance import (
    calculate_roic, calculate_roic_a_share, calculate_roic_hk, calculate_roic_us,
    get_financial_summary_us, get_cashflow_data_us,
    get_financial_summary_hk, get_cashflow_data_hk
)
from .financial_summary import get_financial_summary
from .cashflow import get_cashflow_data
from .valuation import get_valuation_data, get_valuation_data_fast
from .market import get_current_price, get_history_price

__all__ = [
    'calculate_roic',
    'calculate_roic_a_share',
    'calculate_roic_hk',
    'calculate_roic_us',
    'get_financial_summary',
    'get_financial_summary_us',
    'get_financial_summary_hk',
    'get_cashflow_data',
    'get_cashflow_data_us',
    'get_cashflow_data_hk',
    'get_valuation_data',
    'get_valuation_data_fast',
    'get_current_price',
    'get_history_price',
]