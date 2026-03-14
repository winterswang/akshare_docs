"""
现金流数据接口 (Cashflow Data)
支持多数据源路由：TuShare → AkShare(新浪) → 东方财富API(兜底)
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from akshare_service.infra.cache import get_cache
from akshare_service.adapters.tushare_adapter import (
    get_cashflow_data_tushare,
    is_tushare_available
)


# 请求间隔控制
_last_request_time = 0
REQUEST_INTERVAL = 1.0


def _rate_limit():
    """请求限速"""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def get_cashflow_data(code: str, years: int = 5, use_cache: bool = True, 
                      cache_ttl: int = 3600) -> Dict[str, Any]:
    """
    获取现金流数据（标准化输出）
    
    数据源优先级：东方财富API → AkShare(新浪) → AkShare(东财)
    
    Args:
        code: 股票代码
        years: 获取年数
        use_cache: 是否使用缓存
        cache_ttl: 缓存过期时间（秒）
    """
    cache_key = f"cashflow_data:{code}:{years}"
    
    if use_cache:
        cache = get_cache()
        cached = cache.get(cache_key)
        if cached:
            print(f"[Cache] 命中缓存: {cache_key}")
            return cached
    
    errors = []
    
    # 1. 优先使用东方财富 API
    print("[Router] 尝试东方财富 API...")
    result, em_errors = _get_cashflow_data_eastmoney(code, years)
    if result and result.get('annual_data'):
        result['source'] = 'EastMoney.API'
        if use_cache:
            get_cache().set(cache_key, result, cache_ttl)
        return result
    errors.extend(em_errors)
    print(f"[Router] 东方财富 API 失败: {em_errors}")
    
    # 2. 尝试 AkShare 新浪
    print("[Router] 尝试 AkShare 新浪...")
    result, sina_errors = _get_cashflow_data_sina(code, years)
    if result and result.get('annual_data'):
        if use_cache:
            get_cache().set(cache_key, result, cache_ttl)
        return result
    errors.extend(sina_errors)
    print(f"[Router] AkShare 新浪失败: {sina_errors}")
    
    return _error_response(code, errors)


def _get_cashflow_data_sina(code: str, years: int) -> Tuple[Dict[str, Any], List[str]]:
    """从新浪 API 获取现金流数据"""
    errors = []
    market = 'sh' if code.startswith('6') else 'sz'
    sina_code = f"{market}{code}"
    
    _rate_limit()
    try:
        df_cashflow = ak.stock_financial_report_sina(stock=sina_code, symbol='现金流量表')
        if df_cashflow is None or df_cashflow.empty:
            return None, ["新浪现金流量表为空"]
        df_cashflow['报告日'] = pd.to_datetime(df_cashflow['报告日'])
        df_cashflow = df_cashflow[df_cashflow['报告日'].dt.month == 12]
    except Exception as e:
        return None, [f"新浪现金流量表获取失败: {e}"]
    
    _rate_limit()
    try:
        df_profit = ak.stock_financial_report_sina(stock=sina_code, symbol='利润表')
        if df_profit is not None and not df_profit.empty:
            df_profit['报告日'] = pd.to_datetime(df_profit['报告日'])
            df_profit = df_profit[df_profit['报告日'].dt.month == 12]
    except Exception as e:
        df_profit = None
        errors.append(f"利润表获取失败: {e}")
    
    available_years = sorted(df_cashflow['报告日'].dt.year.unique(), reverse=True)[:years]
    annual_data = []
    
    for year in sorted(available_years):
        try:
            cashflow_row = df_cashflow[df_cashflow['报告日'].dt.year == year].iloc[0]
            
            operating_cf = _safe_float(cashflow_row.get('经营活动产生的现金流量净额', 0))
            investing_cf = _safe_float(cashflow_row.get('投资活动产生的现金流量净额', 0))
            financing_cf = _safe_float(cashflow_row.get('筹资活动产生的现金流量净额', 0))
            capex = _safe_float(cashflow_row.get('购建固定资产、无形资产和其他长期资产所支付的现金', 0))
            free_cf = operating_cf - capex
            
            net_profit = 0
            if df_profit is not None:
                try:
                    profit_row = df_profit[df_profit['报告日'].dt.year == year].iloc[0]
                    net_profit = _safe_float(profit_row.get('归属于母公司所有者的净利润', 0))
                except:
                    pass
            
            fcf_to_netprofit = (free_cf / net_profit * 100) if net_profit > 0 else 0
            
            year_data = {
                'year': _safe_int(year),
                'operating_cashflow': {'value': round(operating_cf / 100000000, 2), 'unit': '亿元'},
                'investing_cashflow': {'value': round(investing_cf / 100000000, 2), 'unit': '亿元'},
                'financing_cashflow': {'value': round(financing_cf / 100000000, 2), 'unit': '亿元'},
                'capital_expenditure': {'value': round(capex / 100000000, 2), 'unit': '亿元'},
                'free_cashflow': {'value': round(free_cf / 100000000, 2), 'unit': '亿元'},
                'fcf_to_netprofit': {'value': round(fcf_to_netprofit, 2), 'unit': '%'}
            }
            annual_data.append(year_data)
        except (IndexError, KeyError) as e:
            errors.append(f"处理 {year} 年数据失败: {e}")
            continue
    
    return {
        'code': code,
        'source': 'AkShare.stock_financial_report_sina',
        'fetched_at': datetime.now().isoformat(),
        'annual_data': list(reversed(annual_data)),
        'errors': errors if errors else None
    }, errors


def _get_cashflow_data_eastmoney(code: str, years: int) -> Tuple[Dict[str, Any], List[str]]:
    """从东方财富 API 获取现金流数据（兜底方案）"""
    errors = []
    
    try:
        from akshare_service.crawlers.eastmoney_api import EastMoneyAPI
        api = EastMoneyAPI()
        
        # 获取现金流量表
        df_cashflow = api.get_cashflow_statement(code)
        if df_cashflow is None or df_cashflow.empty:
            return None, ["东方财富现金流量表为空"]
        
        # 筛选年报数据
        df_cashflow_annual = df_cashflow[df_cashflow['report_date'].astype(str).str.contains('-12-')]
        
        annual_data = []
        for i in range(min(years, len(df_cashflow_annual))):
            try:
                row = df_cashflow_annual.iloc[i]
                
                operating_cf = _safe_float(row.get('operating_cf', 0))
                investing_cf = _safe_float(row.get('investing_cf', 0))
                financing_cf = _safe_float(row.get('financing_cf', 0))
                
                # 自由现金流 = 经营现金流 - 投资现金流（简化计算）
                free_cf = operating_cf + investing_cf if investing_cf < 0 else operating_cf
                
                report_date = str(row.get('report_date', ''))
                year = int(report_date[:4]) if len(report_date) >= 4 else 0
                
                year_data = {
                    'year': year,
                    'operating_cashflow': {'value': round(operating_cf / 1e8, 2), 'unit': '亿元'},
                    'investing_cashflow': {'value': round(investing_cf / 1e8, 2), 'unit': '亿元'},
                    'financing_cashflow': {'value': round(financing_cf / 1e8, 2), 'unit': '亿元'},
                    'free_cashflow': {'value': round(free_cf / 1e8, 2), 'unit': '亿元'},
                }
                annual_data.append(year_data)
            except Exception as e:
                errors.append(f"处理数据失败: {e}")
                continue
        
        return {
            'code': code,
            'source': 'EastMoney.API',
            'fetched_at': datetime.now().isoformat(),
            'annual_data': annual_data,
            'errors': errors if errors else None
        }, errors
        
    except Exception as e:
        return None, [f"东方财富 API 获取失败: {e}"]


def _safe_float(value) -> float:
    if pd.isna(value) if not isinstance(value, (int, float)) else False:
        return 0.0
    try:
        return float(value)
    except:
        return 0.0


def _safe_int(value) -> int:
    try:
        return int(value)
    except:
        return 0


def _error_response(code: str, errors: List[str]) -> Dict[str, Any]:
    return {
        'code': code,
        'source': 'MultiSource',
        'fetched_at': datetime.now().isoformat(),
        'annual_data': [],
        'errors': errors
    }


if __name__ == '__main__':
    print("=== 测试现金流数据（多数据源路由）===")
    result = get_cashflow_data("300760", years=3)
    print(f"数据来源: {result.get('source')}")
    print(f"年份数量: {len(result.get('annual_data', []))}")
    if result.get('errors'):
        print(f"错误: {result['errors']}")