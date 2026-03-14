"""
东方财富数据 API 封装
直接调用东方财富 datacenter API，无需爬取网页
作为 AkShare 接口的兜底方案
"""

import requests
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime
import time


class EastMoneyAPI:
    """东方财富数据 API"""
    
    BASE_URL = "https://datacenter.eastmoney.com/api/data/v1/get"
    
    # 报告类型映射
    REPORT_TYPES = {
        "income": "RPT_DMSK_FN_INCOME",        # 利润表
        "balance": "RPT_DMSK_FN_BALANCE",       # 资产负债表
        "cashflow": "RPT_DMSK_FN_CASHFLOW",     # 现金流量表
        "indicator": "RPT_LICO_FN_CPD",         # 财务指标
        "profit_yearly": "RPT_DMSK_FN_INCOME",  # 年度利润表
        "forecast": "RPT_PUBLIC_OP_NEWPREDICT", # 业绩预告
        "valuation": "RPT_VALUE_ANALYSIS",      # 估值分析
    }
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://data.eastmoney.com/',
        })
    
    def _request(self, params: dict) -> Optional[dict]:
        """发送请求"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get('success') and data.get('result'):
                    return data['result']
                else:
                    return None
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                print(f"请求失败: {e}")
                return None
        
        return None
    
    def get_financial_indicator(self, code: str, pagesize: int = 50) -> pd.DataFrame:
        """
        获取财务指标（业绩报表）
        
        Args:
            code: 股票代码，如 "300760"
            pagesize: 返回条数
        
        Returns:
            DataFrame 包含：报告期、EPS、ROE、营收、净利润、毛利率等
        """
        params = {
            "reportName": self.REPORT_TYPES["indicator"],
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
            "pageSize": pagesize,
            "pageNumber": 1
        }
        
        result = self._request(params)
        if not result or not result.get('data'):
            return pd.DataFrame()
        
        df = pd.DataFrame(result['data'])
        
        # 字段映射
        column_map = {
            'REPORTDATE': 'report_date',
            'SECURITY_CODE': 'code',
            'SECURITY_NAME_ABBR': 'name',
            'BASIC_EPS': 'eps',
            'WEIGHTAVG_ROE': 'roe',
            'TOTAL_OPERATE_INCOME': 'revenue',
            'PARENT_NETPROFIT': 'net_profit',
            'XSMLL': 'gross_margin',
            'BPS': 'bps',
            'MGJYXJJE': 'ocf_per_share',
            'YSTZ': 'revenue_yoy',
            'SJLTZ': 'profit_yoy',
        }
        
        df = df.rename(columns=column_map)
        
        # 转换数值
        df['revenue'] = df['revenue'] / 1e8  # 转为亿元
        df['net_profit'] = df['net_profit'] / 1e8
        
        return df
    
    def get_balance_sheet(self, code: str, pagesize: int = 20) -> pd.DataFrame:
        """
        获取资产负债表
        
        Args:
            code: 股票代码
            pagesize: 返回条数
        
        Returns:
            DataFrame 包含：总资产、总负债、股东权益等
        """
        params = {
            "reportName": self.REPORT_TYPES["balance"],
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
            "pageSize": pagesize,
            "pageNumber": 1
        }
        
        result = self._request(params)
        if not result or not result.get('data'):
            return pd.DataFrame()
        
        df = pd.DataFrame(result['data'])
        
        # 字段映射
        column_map = {
            'REPORT_DATE': 'report_date',
            'REPORTDATE': 'report_date',  # 兼容两种格式
            'SECURITY_CODE': 'code',
            'TOTAL_ASSETS': 'total_assets',
            'TOTAL_LIABILITIES': 'total_liabilities',
            'TOTAL_EQUITY': 'total_equity',
            'MONETARYFUNDS': 'cash',
            'TOTAL_CURRENT_ASSETS': 'current_assets',
            'TOTAL_CURRENT_LIABILITIES': 'current_liabilities',
        }
        
        df = df.rename(columns=column_map)
        
        # 转换数值（转为亿元）
        for col in ['total_assets', 'total_liabilities', 'total_equity', 'cash', 
                    'current_assets', 'current_liabilities']:
            if col in df.columns:
                df[col] = df[col] / 1e8
        
        return df
    
    def get_income_statement(self, code: str, pagesize: int = 20) -> pd.DataFrame:
        """
        获取利润表
        
        Args:
            code: 股票代码
            pagesize: 返回条数
        
        Returns:
            DataFrame 包含：营业收入、营业利润、净利润等
        """
        params = {
            "reportName": self.REPORT_TYPES["income"],
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
            "pageSize": pagesize,
            "pageNumber": 1
        }
        
        result = self._request(params)
        if not result or not result.get('data'):
            return pd.DataFrame()
        
        df = pd.DataFrame(result['data'])
        
        # 字段映射
        column_map = {
            'REPORT_DATE': 'report_date',
            'REPORTDATE': 'report_date',  # 兼容两种格式
            'SECURITY_CODE': 'code',
            'TOTAL_OPERATE_INCOME': 'revenue',
            'TOTAL_OPERATE_COST': 'operate_cost',
            'OPERATE_PROFIT': 'operate_profit',
            'TOTAL_PROFIT': 'total_profit',
            'PARENT_NETPROFIT': 'net_profit',
            'INCOME_TAX': 'income_tax',
        }
        
        df = df.rename(columns=column_map)
        
        # 转换数值
        for col in ['revenue', 'operate_cost', 'operate_profit', 'total_profit', 'net_profit', 'income_tax']:
            if col in df.columns:
                df[col] = df[col] / 1e8
        
        return df
    
    def get_cashflow_statement(self, code: str, pagesize: int = 20) -> pd.DataFrame:
        """
        获取现金流量表
        
        Args:
            code: 股票代码
            pagesize: 返回条数
        
        Returns:
            DataFrame 包含：经营现金流、投资现金流、筹资现金流等
        """
        params = {
            "reportName": self.REPORT_TYPES["cashflow"],
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
            "pageSize": pagesize,
            "pageNumber": 1
        }
        
        result = self._request(params)
        if not result or not result.get('data'):
            return pd.DataFrame()
        
        df = pd.DataFrame(result['data'])
        
        # 字段映射
        column_map = {
            'REPORT_DATE': 'report_date',
            'REPORTDATE': 'report_date',  # 兼容两种格式
            'SECURITY_CODE': 'code',
            'NETCASH_OPERATE': 'operating_cf',
            'NETCASH_INVEST': 'investing_cf',
            'NETCASH_FINANCE': 'financing_cf',
        }
        
        df = df.rename(columns=column_map)
        
        return df
    
    def get_forecast(self, code: str, pagesize: int = 20) -> pd.DataFrame:
        """
        获取业绩预告
        
        Args:
            code: 股票代码
            pagesize: 返回条数
        
        Returns:
            DataFrame 包含：预告日期、预告类型、预测金额等
        """
        params = {
            "reportName": self.REPORT_TYPES["forecast"],
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
            "pageSize": pagesize,
            "pageNumber": 1
        }
        
        result = self._request(params)
        if not result or not result.get('data'):
            return pd.DataFrame()
        
        df = pd.DataFrame(result['data'])
        
        # 字段映射
        column_map = {
            'SECURITY_CODE': 'code',
            'SECURITY_NAME_ABBR': 'name',
            'NOTICE_DATE': 'notice_date',
            'REPORT_DATE': 'report_date',
            'PREDICT_FINANCE': 'predict_type',
            'PREDICT_AMT_LOWER': 'predict_amount_lower',
            'PREDICT_AMT_UPPER': 'predict_amount_upper',
            'ADD_AMP_LOWER': 'growth_rate_lower',
            'ADD_AMP_UPPER': 'growth_rate_upper',
            'PREDICT_CONTENT': 'content',
            'CHANGE_REASON_EXPLAIN': 'reason',
        }
        
        df = df.rename(columns=column_map)
        
        # 转换金额为亿元
        for col in ['predict_amount_lower', 'predict_amount_upper']:
            if col in df.columns:
                df[col] = df[col] / 1e8
        
        return df
    
    def get_valuation(self, code: str, pagesize: int = 10) -> pd.DataFrame:
        """
        获取估值分析数据
        
        Args:
            code: 股票代码
            pagesize: 返回条数
        
        Returns:
            DataFrame 包含：PE、PB、PS等估值指标
        """
        params = {
            "reportName": self.REPORT_TYPES["valuation"],
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
            "pageSize": pagesize,
            "pageNumber": 1
        }
        
        result = self._request(params)
        if not result or not result.get('data'):
            return pd.DataFrame()
        
        df = pd.DataFrame(result['data'])
        
        # 字段映射
        column_map = {
            'SECURITY_CODE': 'code',
            'REPORT': 'report_period',
            'STARTDATE': 'start_date',
            'ENDDATE': 'end_date',
            'PEAVG': 'pe_avg',
            'PEMAX': 'pe_max',
            'PEMIN': 'pe_min',
            'PETTM': 'pe_ttm',
            'PBAVG': 'pb_avg',
            'PBMAX': 'pb_max',
            'PBMIN': 'pb_min',
            'PBMRQ': 'pb_mrq',
            'PSAVG': 'ps_avg',
            'PSMAX': 'ps_max',
            'PSMIN': 'ps_min',
            'PSTTM': 'ps_ttm',
        }
        
        df = df.rename(columns=column_map)
        
        return df
    
    def get_all_financial_data(self, code: str) -> Dict[str, pd.DataFrame]:
        """
        获取全部财务数据
        
        Args:
            code: 股票代码
        
        Returns:
            dict: {
                'indicator': 财务指标,
                'balance': 资产负债表,
                'income': 利润表,
                'cashflow': 现金流量表,
                'forecast': 业绩预告,
                'valuation': 估值分析
            }
        """
        return {
            'indicator': self.get_financial_indicator(code),
            'balance': self.get_balance_sheet(code),
            'income': self.get_income_statement(code),
            'cashflow': self.get_cashflow_statement(code),
            'forecast': self.get_forecast(code),
            'valuation': self.get_valuation(code),
        }


# 便捷函数
def get_financial_indicator(code: str) -> pd.DataFrame:
    """获取财务指标"""
    api = EastMoneyAPI()
    return api.get_financial_indicator(code)


def get_balance_sheet(code: str) -> pd.DataFrame:
    """获取资产负债表"""
    api = EastMoneyAPI()
    return api.get_balance_sheet(code)


def get_income_statement(code: str) -> pd.DataFrame:
    """获取利润表"""
    api = EastMoneyAPI()
    return api.get_income_statement(code)


def get_forecast(code: str) -> pd.DataFrame:
    """获取业绩预告"""
    api = EastMoneyAPI()
    return api.get_forecast(code)


def get_valuation(code: str) -> pd.DataFrame:
    """获取估值分析"""
    api = EastMoneyAPI()
    return api.get_valuation(code)


def get_all_financial_data(code: str) -> Dict[str, pd.DataFrame]:
    """获取全部财务数据"""
    api = EastMoneyAPI()
    return api.get_all_financial_data(code)