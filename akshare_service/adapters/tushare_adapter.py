"""
TuShare 数据源适配器
提供标准化的 TuShare 接口封装
"""

import tushare as ts
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import os

# TuShare Token 配置
# 优先从环境变量获取，否则使用默认值
TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN', '')

_pro = None

def get_tushare_pro():
    """获取 TuShare Pro API 实例"""
    global _pro
    if _pro is None and TUSHARE_TOKEN:
        _pro = ts.pro_api(TUSHARE_TOKEN)
    return _pro


def is_tushare_available() -> bool:
    """检查 TuShare 是否可用"""
    return bool(TUSHARE_TOKEN) and get_tushare_pro() is not None


def get_financial_summary_tushare(code: str, years: int = 5) -> Tuple[Dict[str, Any], List[str]]:
    """
    使用 TuShare 获取财务指标
    
    Args:
        code: 股票代码
        years: 获取年数
    
    Returns:
        (结果字典, 错误列表)
    """
    errors = []
    pro = get_tushare_pro()
    
    if not pro:
        return None, ["TuShare Token 未配置"]
    
    try:
        # 转换股票代码格式
        ts_code = _convert_code_to_tushare(code)
        
        # 获取财务指标数据
        df = pro.fina_indicator(ts_code=ts_code, fields=[
            'ts_code', 'ann_date', 'end_date',
            'total_revenue', 'revenue', 'n_income', 'n_income_attr_p',
            'grossprofit_margin', 'netprofit_margin', 'roe', 'roa',
            'total_assets', 'total_hldr_eqy_exc_min_int',
            'total_liab', 'current_ratio', 'debt_to_assets'
        ])
        
        if df is None or df.empty:
            return None, ["TuShare 返回空数据"]
        
        # 处理数据
        return _process_tushare_financial(code, df, years, errors)
        
    except Exception as e:
        return None, [f"TuShare 获取失败: {e}"]


def get_cashflow_data_tushare(code: str, years: int = 5) -> Tuple[Dict[str, Any], List[str]]:
    """
    使用 TuShare 获取现金流数据
    
    Args:
        code: 股票代码
        years: 获取年数
    
    Returns:
        (结果字典, 错误列表)
    """
    errors = []
    pro = get_tushare_pro()
    
    if not pro:
        return None, ["TuShare Token 未配置"]
    
    try:
        ts_code = _convert_code_to_tushare(code)
        
        # 获取现金流量表
        df = pro.cashflow(ts_code=ts_code, fields=[
            'ts_code', 'ann_date', 'end_date',
            'n_cashflow_act', 'n_cashflow_inv_act', 'n_cash_flows_fnc_act',
            'cash_pay_acq_const_fi'
        ])
        
        # 获取利润表（用于计算 FCF/净利润）
        df_profit = pro.income(ts_code=ts_code, fields=[
            'ts_code', 'end_date', 'n_income_attr_p'
        ])
        
        if df is None or df.empty:
            return None, ["TuShare 现金流返回空数据"]
        
        return _process_tushare_cashflow(code, df, df_profit, years, errors)
        
    except Exception as e:
        return None, [f"TuShare 现金流获取失败: {e}"]


def _convert_code_to_tushare(code: str) -> str:
    """转换股票代码格式: 300760 -> 300760.SZ"""
    if '.' in code:
        return code
    if code.startswith('6'):
        return f"{code}.SH"
    else:
        return f"{code}.SZ"


def _process_tushare_financial(code: str, df: pd.DataFrame, years: int, 
                                errors: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """处理 TuShare 财务数据"""
    # 筛选年报数据（end_date 以 1231 结尾）
    df = df[df['end_date'].str.endswith('1231')]
    
    # 按日期排序，取最近 N 年
    df = df.sort_values('end_date', ascending=False).head(years)
    
    annual_data = []
    prev_year_data = None
    
    for _, row in df.iterrows():
        try:
            year = int(row['end_date'][:4])
            
            revenue = _safe_float(row.get('revenue') or row.get('total_revenue', 0))
            net_profit = _safe_float(row.get('n_income_attr_p', 0))
            gross_margin = _safe_float(row.get('grossprofit_margin', 0))
            net_margin = _safe_float(row.get('netprofit_margin', 0))
            roe = _safe_float(row.get('roe', 0))
            total_assets = _safe_float(row.get('total_assets', 0))
            total_equity = _safe_float(row.get('total_hldr_eqy_exc_min_int', 0))
            total_liab = _safe_float(row.get('total_liab', 0))
            debt_ratio = _safe_float(row.get('debt_to_assets', 0))
            current_ratio = _safe_float(row.get('current_ratio', 0))
            
            # 同比增长
            yoy_revenue = None
            yoy_profit = None
            if prev_year_data:
                if prev_year_data.get('revenue', 0) > 0:
                    yoy_revenue = round((revenue - prev_year_data['revenue']) / prev_year_data['revenue'] * 100, 2)
                if prev_year_data.get('net_profit', 0) > 0:
                    yoy_profit = round((net_profit - prev_year_data['net_profit']) / prev_year_data['net_profit'] * 100, 2)
            
            year_data = {
                'year': year,
                'revenue': {'value': round(revenue / 100000000, 2), 'unit': '亿元', 'yoy_growth': yoy_revenue},
                'net_profit': {'value': round(net_profit / 100000000, 2), 'unit': '亿元', 'yoy_growth': yoy_profit},
                'gross_margin': {'value': round(gross_margin, 2) if gross_margin else None, 'unit': '%'},
                'net_margin': {'value': round(net_margin, 2) if net_margin else None, 'unit': '%'},
                'roe': {'value': round(roe, 2) if roe else None, 'unit': '%'},
                'total_assets': {'value': round(total_assets / 100000000, 2), 'unit': '亿元'},
                'total_equity': {'value': round(total_equity / 100000000, 2), 'unit': '亿元'},
                'total_liabilities': {'value': round(total_liab / 100000000, 2), 'unit': '亿元'},
                'debt_ratio': {'value': round(debt_ratio * 100, 2) if debt_ratio else None, 'unit': '%'},
                'current_ratio': {'value': round(current_ratio, 2) if current_ratio else None, 'unit': '倍'}
            }
            
            annual_data.append(year_data)
            prev_year_data = {'revenue': revenue, 'net_profit': net_profit}
            
        except Exception as e:
            errors.append(f"处理 {row.get('end_date', 'unknown')} 数据失败: {e}")
            continue
    
    # 按年份升序排列
    annual_data = list(reversed(annual_data))
    
    return {
        'code': code,
        'name': '',
        'source': 'TuShare.fina_indicator',
        'fetched_at': datetime.now().isoformat(),
        'annual_data': annual_data,
        'errors': errors if errors else None
    }, errors


def _process_tushare_cashflow(code: str, df: pd.DataFrame, df_profit: Optional[pd.DataFrame],
                               years: int, errors: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """处理 TuShare 现金流数据"""
    # 筛选年报数据
    df = df[df['end_date'].str.endswith('1231')]
    df = df.sort_values('end_date', ascending=False).head(years)
    
    annual_data = []
    
    for _, row in df.iterrows():
        try:
            year = int(row['end_date'][:4])
            
            operating_cf = _safe_float(row.get('n_cashflow_act', 0))
            investing_cf = _safe_float(row.get('n_cashflow_inv_act', 0))
            financing_cf = _safe_float(row.get('n_cash_flows_fnc_act', 0))
            capex = _safe_float(row.get('cash_pay_acq_const_fi', 0))
            free_cf = operating_cf - capex
            
            # 获取净利润
            net_profit = 0
            if df_profit is not None and not df_profit.empty:
                profit_row = df_profit[df_profit['end_date'] == row['end_date']]
                if not profit_row.empty:
                    net_profit = _safe_float(profit_row.iloc[0].get('n_income_attr_p', 0))
            
            fcf_to_netprofit = (free_cf / net_profit * 100) if net_profit > 0 else 0
            
            year_data = {
                'year': year,
                'operating_cashflow': {'value': round(operating_cf / 100000000, 2), 'unit': '亿元'},
                'investing_cashflow': {'value': round(investing_cf / 100000000, 2), 'unit': '亿元'},
                'financing_cashflow': {'value': round(financing_cf / 100000000, 2), 'unit': '亿元'},
                'capital_expenditure': {'value': round(capex / 100000000, 2), 'unit': '亿元'},
                'free_cashflow': {'value': round(free_cf / 100000000, 2), 'unit': '亿元'},
                'fcf_to_netprofit': {'value': round(fcf_to_netprofit, 2), 'unit': '%'}
            }
            
            annual_data.append(year_data)
            
        except Exception as e:
            errors.append(f"处理 {row.get('end_date', 'unknown')} 数据失败: {e}")
            continue
    
    return {
        'code': code,
        'source': 'TuShare.cashflow',
        'fetched_at': datetime.now().isoformat(),
        'annual_data': list(reversed(annual_data)),
        'errors': errors if errors else None
    }, errors


def _safe_float(value) -> float:
    """安全转换为浮点数"""
    if value is None or pd.isna(value):
        return 0.0
    try:
        return float(value)
    except:
        return 0.0


# 测试入口
if __name__ == '__main__':
    import json
    
    if not TUSHARE_TOKEN:
        print("请设置 TUSHARE_TOKEN 环境变量")
        print("获取方式: https://tushare.pro 注册后获取 token")
    else:
        print("=== 测试 TuShare 财务指标 ===")
        result, errors = get_financial_summary_tushare("300760", years=3)
        if result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"获取失败: {errors}")