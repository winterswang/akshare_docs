"""
财务数据路由器
多数据源自动切换：TuShare → AkShare → 东方财富 API

优先级：
1. TuShare（需Token）
2. AkShare
3. 东方财富 API（兜底）
"""

import pandas as pd
from typing import Optional, Dict, Any
import os


class FinancialRouter:
    """财务数据多源路由器"""
    
    def __init__(self):
        self.tushare_token = os.environ.get('TUSHARE_TOKEN')
        self._akshare = None
        self._eastmoney = None
        self._tushare = None
    
    @property
    def akshare(self):
        """延迟加载 AkShare"""
        if self._akshare is None:
            try:
                import akshare as ak
                self._akshare = ak
            except ImportError:
                pass
        return self._akshare
    
    @property
    def eastmoney(self):
        """延迟加载东方财富 API"""
        if self._eastmoney is None:
            from akshare_service.crawlers.eastmoney_api import EastMoneyAPI
            self._eastmoney = EastMoneyAPI()
        return self._eastmoney
    
    def get_financial_indicator(self, code: str, years: int = 5) -> pd.DataFrame:
        """
        获取财务指标（多源路由）
        
        Args:
            code: 股票代码
            years: 年数
        
        Returns:
            DataFrame
        """
        # 1. 尝试 TuShare
        if self.tushare_token:
            try:
                from akshare_service.adapters.tushare_adapter import TushareAdapter
                adapter = TushareAdapter(self.tushare_token)
                df = adapter.get_financial_indicator(code, years)
                if not df.empty:
                    df['source'] = 'TuShare'
                    return df
            except Exception as e:
                print(f"TuShare 失败: {e}")
        
        # 2. 尝试 AkShare
        if self.akshare:
            try:
                df = self.akshare.stock_financial_analysis_indicator_em(symbol=code)
                if df is not None and not df.empty:
                    df['source'] = 'AkShare'
                    return df
            except Exception as e:
                print(f"AkShare 失败: {e}")
        
        # 3. 兜底：东方财富 API
        print("使用东方财富 API 兜底...")
        df = self.eastmoney.get_financial_indicator(code)
        if not df.empty:
            df['source'] = 'EastMoney'
        return df
    
    def get_balance_sheet(self, code: str) -> pd.DataFrame:
        """获取资产负债表（多源路由）"""
        # 尝试 AkShare
        if self.akshare:
            try:
                df = self.akshare.stock_balance_sheet_by_yearly_em(symbol=code)
                if df is not None and not df.empty:
                    df['source'] = 'AkShare'
                    return df
            except Exception as e:
                print(f"AkShare 失败: {e}")
        
        # 兜底：东方财富 API
        df = self.eastmoney.get_balance_sheet(code)
        if not df.empty:
            df['source'] = 'EastMoney'
        return df
    
    def get_income_statement(self, code: str) -> pd.DataFrame:
        """获取利润表（多源路由）"""
        # 尝试 AkShare
        if self.akshare:
            try:
                df = self.akshare.stock_profit_sheet_by_yearly_em(symbol=code)
                if df is not None and not df.empty:
                    df['source'] = 'AkShare'
                    return df
            except Exception as e:
                print(f"AkShare 失败: {e}")
        
        # 兜底：东方财富 API
        df = self.eastmoney.get_income_statement(code)
        if not df.empty:
            df['source'] = 'EastMoney'
        return df
    
    def get_all_financial_data(self, code: str) -> Dict[str, pd.DataFrame]:
        """获取全部财务数据"""
        return {
            'indicator': self.get_financial_indicator(code),
            'balance': self.get_balance_sheet(code),
            'income': self.get_income_statement(code),
        }


# 便捷函数
_router = None

def get_financial_data(code: str, data_type: str = 'indicator') -> pd.DataFrame:
    """
    获取财务数据（自动路由）
    
    Args:
        code: 股票代码
        data_type: 数据类型 (indicator/balance/income)
    
    Returns:
        DataFrame
    """
    global _router
    if _router is None:
        _router = FinancialRouter()
    
    if data_type == 'indicator':
        return _router.get_financial_indicator(code)
    elif data_type == 'balance':
        return _router.get_balance_sheet(code)
    elif data_type == 'income':
        return _router.get_income_statement(code)
    else:
        return pd.DataFrame()