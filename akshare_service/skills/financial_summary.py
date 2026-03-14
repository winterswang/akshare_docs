"""
核心财务指标接口 (Financial Summary)
支持多数据源路由：TuShare → AkShare(新浪) → AkShare(东财) → 东方财富API(兜底)
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
    get_financial_summary_tushare,
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


def get_financial_summary(code: str, years: int = 5, fetch_name: bool = False,
                          use_cache: bool = True, cache_ttl: int = 3600) -> Dict[str, Any]:
    """
    获取核心财务指标（标准化输出）
    
    数据源优先级：TuShare → AkShare(新浪) → AkShare(东财) → 东方财富API(兜底)
    
    Args:
        code: 股票代码
        years: 获取年数
        fetch_name: 是否获取股票名称
        use_cache: 是否使用缓存
        cache_ttl: 缓存过期时间（秒）
    
    Returns:
        标准化财务数据字典
    """
    cache_key = f"financial_summary:{code}:{years}"
    
    # 尝试从缓存获取
    if use_cache:
        cache = get_cache()
        cached = cache.get(cache_key)
        if cached:
            print(f"[Cache] 命中缓存: {cache_key}")
            return cached
    
    errors = []
    
    # 1. 尝试 TuShare
    if is_tushare_available():
        print("[Router] 尝试 TuShare...")
        result, ts_errors = get_financial_summary_tushare(code, years)
        if result and result.get('annual_data'):
            if use_cache:
                get_cache().set(cache_key, result, cache_ttl)
            return result
        errors.extend(ts_errors)
        print(f"[Router] TuShare 失败: {ts_errors}")
    
    # 2. 尝试 AkShare 新浪
    print("[Router] 尝试 AkShare 新浪...")
    result, sina_errors = _get_financial_summary_sina(code, years, fetch_name)
    if result and result.get('annual_data'):
        result['source'] = 'AkShare.stock_financial_report_sina'
        if use_cache:
            get_cache().set(cache_key, result, cache_ttl)
        return result
    errors.extend(sina_errors)
    print(f"[Router] AkShare 新浪失败: {sina_errors}")
    
    # 3. 尝试 AkShare 东财
    print("[Router] 尝试 AkShare 东财...")
    result, em_errors = _get_financial_summary_em(code, years, fetch_name)
    if result and result.get('annual_data'):
        result['source'] = 'AkShare.stock_profit_sheet_by_yearly_em'
        if use_cache:
            get_cache().set(cache_key, result, cache_ttl)
        return result
    errors.extend(em_errors)
    print(f"[Router] AkShare 东财失败: {em_errors}")
    
    # 4. 兜底：东方财富 API（直接调用，不走 AkShare）
    print("[Router] 尝试东方财富 API 兜底...")
    result, eastmoney_errors = _get_financial_summary_eastmoney(code, years, fetch_name)
    if result and result.get('annual_data'):
        result['source'] = 'EastMoney.API'
        if use_cache:
            get_cache().set(cache_key, result, cache_ttl)
        return result
    errors.extend(eastmoney_errors)
    
    return _error_response(code, errors)


def _get_financial_summary_sina(code: str, years: int, fetch_name: bool) -> Tuple[Dict[str, Any], List[str]]:
    """从新浪 API 获取财务数据"""
    errors = []
    market = 'sh' if code.startswith('6') else 'sz'
    sina_code = f"{market}{code}"
    
    _rate_limit()
    try:
        df_profit = ak.stock_financial_report_sina(stock=sina_code, symbol='利润表')
        if df_profit is None or df_profit.empty:
            return None, ["新浪利润表为空"]
        df_profit['报告日'] = pd.to_datetime(df_profit['报告日'])
        df_profit = df_profit[df_profit['报告日'].dt.month == 12]
    except Exception as e:
        return None, [f"新浪利润表获取失败: {e}"]
    
    _rate_limit()
    try:
        df_balance = ak.stock_financial_report_sina(stock=sina_code, symbol='资产负债表')
        if df_balance is None or df_balance.empty:
            return None, ["新浪资产负债表为空"]
        df_balance['报告日'] = pd.to_datetime(df_balance['报告日'])
        df_balance = df_balance[df_balance['报告日'].dt.month == 12]
    except Exception as e:
        return None, [f"新浪资产负债表获取失败: {e}"]
    
    stock_name = ""
    if fetch_name:
        stock_name = _get_stock_name(code)
    
    return _process_sina_data(code, stock_name, df_profit, df_balance, years, errors)


def _get_financial_summary_em(code: str, years: int, fetch_name: bool) -> Tuple[Dict[str, Any], List[str]]:
    """从东财 API 获取财务数据"""
    errors = []
    
    _rate_limit()
    try:
        df_profit = ak.stock_profit_sheet_by_yearly_em(symbol=code)
        if df_profit is None or df_profit.empty:
            return None, ["东财利润表为空"]
    except Exception as e:
        return None, [f"东财利润表获取失败: {e}"]
    
    _rate_limit()
    try:
        df_balance = ak.stock_balance_sheet_by_yearly_em(symbol=code)
        if df_balance is None or df_balance.empty:
            return None, ["东财资产负债表为空"]
    except Exception as e:
        return None, [f"东财资产负债表获取失败: {e}"]
    
    stock_name = ""
    if fetch_name:
        stock_name = _get_stock_name(code)
    
    return _process_em_data(code, stock_name, df_profit, df_balance, years, errors)


def _get_financial_summary_eastmoney(code: str, years: int, fetch_name: bool) -> Tuple[Dict[str, Any], List[str]]:
    """从东方财富 API 获取财务数据（兜底方案）"""
    errors = []
    
    try:
        from akshare_service.crawlers.eastmoney_api import EastMoneyAPI
        api = EastMoneyAPI()
        
        # 获取财务指标
        df_indicator = api.get_financial_indicator(code)
        if df_indicator is None or df_indicator.empty:
            return None, ["东方财富财务指标为空"]
        
        # 获取资产负债表
        df_balance = api.get_balance_sheet(code)
        if df_balance is None or df_balance.empty:
            return None, ["东方财富资产负债表为空"]
        
        stock_name = ""
        if fetch_name and not df_indicator.empty:
            stock_name = str(df_indicator.iloc[0].get('name', ''))
        
        return _process_eastmoney_data(code, stock_name, df_indicator, df_balance, years, errors)
        
    except Exception as e:
        return None, [f"东方财富 API 获取失败: {e}"]


def _process_eastmoney_data(code: str, stock_name: str, df_indicator: pd.DataFrame,
                            df_balance: pd.DataFrame, years: int, errors: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """处理东方财富 API 数据"""
    # 只取年报数据
    df_indicator = df_indicator[df_indicator['report_date'].astype(str).str.contains('-12-')]
    df_balance = df_balance[df_balance['report_date'].astype(str).str.contains('-12-')]
    
    available_years = min(len(df_indicator), years)
    annual_data = []
    prev_year_data = None
    
    for i in range(available_years):
        try:
            row = df_indicator.iloc[i]
            balance_row = df_balance[df_balance['report_date'] == row['report_date']].iloc[0] if len(df_balance) > i else None
            
            revenue = _safe_float(row.get('revenue', 0))
            net_profit = _safe_float(row.get('net_profit', 0))
            roe = _safe_float(row.get('roe', 0))
            gross_margin = _safe_float(row.get('gross_margin', 0))
            
            total_assets = _safe_float(balance_row.get('total_assets', 0)) if balance_row is not None else 0
            total_equity = _safe_float(balance_row.get('total_equity', 0)) if balance_row is not None else 0
            total_liabilities = _safe_float(balance_row.get('total_liabilities', 0)) if balance_row is not None else 0
            
            net_margin = (net_profit / revenue * 100) if revenue > 0 else 0
            debt_ratio = (total_liabilities / total_assets * 100) if total_assets > 0 else 0
            
            yoy_revenue = row.get('revenue_yoy')
            yoy_profit = row.get('profit_yoy')
            
            report_date = str(row.get('report_date', ''))
            year = int(report_date[:4]) if len(report_date) >= 4 else 0
            
            year_data = {
                'year': year,
                'revenue': {'value': round(revenue, 2), 'unit': '亿元', 'yoy_growth': yoy_revenue},
                'net_profit': {'value': round(net_profit, 2), 'unit': '亿元', 'yoy_growth': yoy_profit},
                'gross_margin': {'value': round(gross_margin, 2), 'unit': '%'},
                'net_margin': {'value': round(net_margin, 2), 'unit': '%'},
                'roe': {'value': round(roe, 2), 'unit': '%'},
                'total_assets': {'value': round(total_assets, 2), 'unit': '亿元'},
                'total_equity': {'value': round(total_equity, 2), 'unit': '亿元'},
                'total_liabilities': {'value': round(total_liabilities, 2), 'unit': '亿元'},
                'debt_ratio': {'value': round(debt_ratio, 2), 'unit': '%'},
            }
            
            annual_data.append(year_data)
            prev_year_data = {'revenue': revenue, 'net_profit': net_profit}
            
        except (IndexError, KeyError) as e:
            errors.append(f"处理数据失败: {e}")
            continue
    
    return {
        'code': code,
        'name': stock_name,
        'source': 'EastMoney.API',
        'fetched_at': datetime.now().isoformat(),
        'annual_data': annual_data,
        'errors': errors if errors else None
    }, errors


def _process_sina_data(code: str, stock_name: str, df_profit: pd.DataFrame, 
                       df_balance: pd.DataFrame, years: int, errors: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """处理新浪数据"""
    available_years = sorted(df_profit['报告日'].dt.year.unique(), reverse=True)[:years]
    annual_data = []
    prev_year_data = None
    
    for year in sorted(available_years):
        try:
            profit_row = df_profit[df_profit['报告日'].dt.year == year].iloc[0]
            balance_row = df_balance[df_balance['报告日'].dt.year == year].iloc[0]
            
            revenue = _safe_float(profit_row.get('营业收入', 0))
            net_profit = _safe_float(profit_row.get('归属于母公司所有者的净利润', 0))
            operating_cost = _safe_float(profit_row.get('营业成本', 0))
            
            total_assets = _safe_float(balance_row.get('资产总计', 0))
            total_equity = _safe_float(balance_row.get('所有者权益(或股东权益)合计', 0))
            total_liabilities = _safe_float(balance_row.get('负债合计', 0))
            current_assets = _safe_float(balance_row.get('流动资产合计', 0))
            current_liabilities = _safe_float(balance_row.get('流动负债合计', 0))
            
            gross_margin = ((revenue - operating_cost) / revenue * 100) if revenue > 0 else 0
            net_margin = (net_profit / revenue * 100) if revenue > 0 else 0
            roe = (net_profit / total_equity * 100) if total_equity > 0 else 0
            debt_ratio = (total_liabilities / total_assets * 100) if total_assets > 0 else 0
            current_ratio = (current_assets / current_liabilities) if current_liabilities > 0 else 0
            
            yoy_revenue = None
            yoy_profit = None
            if prev_year_data:
                if prev_year_data.get('revenue', 0) > 0:
                    yoy_revenue = round((revenue - prev_year_data['revenue']) / prev_year_data['revenue'] * 100, 2)
                if prev_year_data.get('net_profit', 0) > 0:
                    yoy_profit = round((net_profit - prev_year_data['net_profit']) / prev_year_data['net_profit'] * 100, 2)
            
            year_data = {
                'year': _safe_int(year),
                'revenue': {'value': round(revenue / 100000000, 2), 'unit': '亿元', 'yoy_growth': yoy_revenue},
                'net_profit': {'value': round(net_profit / 100000000, 2), 'unit': '亿元', 'yoy_growth': yoy_profit},
                'gross_margin': {'value': round(gross_margin, 2), 'unit': '%'},
                'net_margin': {'value': round(net_margin, 2), 'unit': '%'},
                'roe': {'value': round(roe, 2), 'unit': '%'},
                'total_assets': {'value': round(total_assets / 100000000, 2), 'unit': '亿元'},
                'total_equity': {'value': round(total_equity / 100000000, 2), 'unit': '亿元'},
                'total_liabilities': {'value': round(total_liabilities / 100000000, 2), 'unit': '亿元'},
                'debt_ratio': {'value': round(debt_ratio, 2), 'unit': '%'},
                'current_ratio': {'value': round(current_ratio, 2), 'unit': '倍'}
            }
            
            annual_data.append(year_data)
            prev_year_data = {'revenue': revenue, 'net_profit': net_profit}
            
        except (IndexError, KeyError) as e:
            errors.append(f"处理 {year} 年数据失败: {e}")
            continue
    
    return {
        'code': code,
        'name': stock_name,
        'source': 'AkShare.stock_financial_report_sina',
        'fetched_at': datetime.now().isoformat(),
        'annual_data': list(reversed(annual_data)),
        'errors': errors if errors else None
    }, errors


def _process_em_data(code: str, stock_name: str, df_profit: pd.DataFrame,
                     df_balance: pd.DataFrame, years: int, errors: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """处理东财数据"""
    df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])
    df_balance['REPORT_DATE'] = pd.to_datetime(df_balance['REPORT_DATE'])
    
    df_profit = df_profit[df_profit['REPORT_DATE'].dt.month == 12]
    df_balance = df_balance[df_balance['REPORT_DATE'].dt.month == 12]
    
    available_years = sorted(df_profit['REPORT_DATE'].dt.year.unique(), reverse=True)[:years]
    annual_data = []
    prev_year_data = None
    
    for year in sorted(available_years):
        try:
            profit_row = df_profit[df_profit['REPORT_DATE'].dt.year == year].iloc[0]
            balance_row = df_balance[df_balance['REPORT_DATE'].dt.year == year].iloc[0]
            
            revenue = _safe_float(profit_row.get('TOTAL_OPERATE_INCOME', 0))
            net_profit = _safe_float(profit_row.get('NETPROFIT', 0))
            operating_cost = _safe_float(profit_row.get('OPERATE_COST', 0))
            
            total_assets = _safe_float(balance_row.get('TOTAL_ASSETS', 0))
            total_equity = _safe_float(balance_row.get('TOTAL_EQUITY', 0))
            total_liabilities = _safe_float(balance_row.get('TOTAL_LIAB', 0))
            current_assets = _safe_float(balance_row.get('TOTAL_CURRENT_ASSETS', 0))
            current_liabilities = _safe_float(balance_row.get('TOTAL_CURRENT_LIAB', 0))
            
            gross_margin = ((revenue - operating_cost) / revenue * 100) if revenue > 0 else 0
            net_margin = (net_profit / revenue * 100) if revenue > 0 else 0
            roe = (net_profit / total_equity * 100) if total_equity > 0 else 0
            debt_ratio = (total_liabilities / total_assets * 100) if total_assets > 0 else 0
            current_ratio = (current_assets / current_liabilities) if current_liabilities > 0 else 0
            
            yoy_revenue = None
            yoy_profit = None
            if prev_year_data:
                if prev_year_data.get('revenue', 0) > 0:
                    yoy_revenue = round((revenue - prev_year_data['revenue']) / prev_year_data['revenue'] * 100, 2)
                if prev_year_data.get('net_profit', 0) > 0:
                    yoy_profit = round((net_profit - prev_year_data['net_profit']) / prev_year_data['net_profit'] * 100, 2)
            
            year_data = {
                'year': _safe_int(year),
                'revenue': {'value': round(revenue / 100000000, 2), 'unit': '亿元', 'yoy_growth': yoy_revenue},
                'net_profit': {'value': round(net_profit / 100000000, 2), 'unit': '亿元', 'yoy_growth': yoy_profit},
                'gross_margin': {'value': round(gross_margin, 2), 'unit': '%'},
                'net_margin': {'value': round(net_margin, 2), 'unit': '%'},
                'roe': {'value': round(roe, 2), 'unit': '%'},
                'total_assets': {'value': round(total_assets / 100000000, 2), 'unit': '亿元'},
                'total_equity': {'value': round(total_equity / 100000000, 2), 'unit': '亿元'},
                'total_liabilities': {'value': round(total_liabilities / 100000000, 2), 'unit': '亿元'},
                'debt_ratio': {'value': round(debt_ratio, 2), 'unit': '%'},
                'current_ratio': {'value': round(current_ratio, 2), 'unit': '倍'}
            }
            
            annual_data.append(year_data)
            prev_year_data = {'revenue': revenue, 'net_profit': net_profit}
            
        except (IndexError, KeyError) as e:
            errors.append(f"处理 {year} 年数据失败: {e}")
            continue
    
    return {
        'code': code,
        'name': stock_name,
        'source': 'AkShare.stock_profit_sheet_by_yearly_em',
        'fetched_at': datetime.now().isoformat(),
        'annual_data': list(reversed(annual_data)),
        'errors': errors if errors else None
    }, errors


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


def _get_stock_name(code: str) -> str:
    try:
        df = ak.stock_zh_a_spot_em()
        stock = df[df['代码'] == code]
        if not stock.empty:
            return str(stock.iloc[0]['名称'])
    except:
        pass
    return ""


def _error_response(code: str, errors: List[str]) -> Dict[str, Any]:
    return {
        'code': code,
        'name': '',
        'source': 'MultiSource',
        'fetched_at': datetime.now().isoformat(),
        'annual_data': [],
        'errors': errors
    }


if __name__ == '__main__':
    print("=== 测试财务指标（多数据源路由）===")
    result = get_financial_summary("300760", years=3)
    print(f"数据来源: {result.get('source')}")
    print(f"年份数量: {len(result.get('annual_data', []))}")
    if result.get('errors'):
        print(f"错误: {result['errors']}")
    print(json.dumps(result, ensure_ascii=False, indent=2))