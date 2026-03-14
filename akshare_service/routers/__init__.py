# 财务数据路由
# 多数据源自动切换：TuShare → AkShare → 东方财富 API

from .financial_router import FinancialRouter, get_financial_data

__all__ = ['FinancialRouter', 'get_financial_data']