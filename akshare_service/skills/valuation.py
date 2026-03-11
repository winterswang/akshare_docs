"""
估值数据接口 (Valuation Data)
提供标准化的估值数据输出，包括股价、PE、PB、市值等。
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from akshare_service.infra.client import robust_api


def get_valuation_data(code: str) -> Dict[str, Any]:
    """
    获取实时估值数据（标准化输出）
    
    Args:
        code: 股票代码（如 "300760"）
    
    Returns:
        标准化估值数据字典
    """
    errors = []
    
    # 尝试东财接口
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            stock = df[df['代码'] == code]
            if not stock.empty:
                row = stock.iloc[0]
                
                price = _safe_float(row.get('最新价', 0))
                pe_ttm = _safe_float(row.get('市盈率-动态', 0))
                pb = _safe_float(row.get('市净率', 0))
                market_cap = _safe_float(row.get('总市值', 0))
                circulating_market_cap = _safe_float(row.get('流通市值', 0))
                
                return {
                    'code': code,
                    'name': str(row.get('名称', '')),
                    'source': 'AkShare.stock_zh_a_spot_em',
                    'fetched_at': datetime.now().isoformat(),
                    'price': {
                        'value': round(price, 2),
                        'unit': '元'
                    },
                    'pe_ttm': {
                        'value': round(pe_ttm, 2) if pe_ttm > 0 else None,
                        'unit': '倍'
                    },
                    'pb': {
                        'value': round(pb, 2) if pb > 0 else None,
                        'unit': '倍'
                    },
                    'market_cap': {
                        'value': round(market_cap / 100000000, 2),
                        'unit': '亿元'
                    },
                    'circulating_market_cap': {
                        'value': round(circulating_market_cap / 100000000, 2),
                        'unit': '亿元'
                    },
                    'change_percent': {
                        'value': round(_safe_float(row.get('涨跌幅', 0)), 2),
                        'unit': '%'
                    },
                    'volume': {
                        'value': round(_safe_float(row.get('成交量', 0)) / 100000000, 2),
                        'unit': '亿股'
                    },
                    'amount': {
                        'value': round(_safe_float(row.get('成交额', 0)) / 100000000, 2),
                        'unit': '亿元'
                    },
                    'errors': None
                }
    except Exception as e:
        errors.append(f"东财接口失败: {e}")
    
    return _error_response(code, errors)


def get_valuation_data_fast(code: str) -> Dict[str, Any]:
    """
    快速获取估值数据（使用新浪接口，更稳定但数据较少）
    
    Args:
        code: 股票代码（如 "300760"）
    
    Returns:
        标准化估值数据字典
    """
    errors = []
    
    try:
        # 新浪实时行情
        market = 'sh' if code.startswith('6') else 'sz'
        sina_code = f"{market}{code}"
        
        df = ak.stock_zh_a_spot()
        if df is not None and not df.empty:
            stock = df[df['code'] == sina_code]
            if not stock.empty:
                row = stock.iloc[0]
                
                return {
                    'code': code,
                    'name': str(row.get('name', '')),
                    'source': 'AkShare.stock_zh_a_spot',
                    'fetched_at': datetime.now().isoformat(),
                    'price': {
                        'value': round(_safe_float(row.get('trade', 0)), 2),
                        'unit': '元'
                    },
                    'pe_ttm': {
                        'value': None,
                        'unit': '倍'
                    },
                    'pb': {
                        'value': None,
                        'unit': '倍'
                    },
                    'market_cap': {
                        'value': None,
                        'unit': '亿元'
                    },
                    'circulating_market_cap': {
                        'value': None,
                        'unit': '亿元'
                    },
                    'change_percent': {
                        'value': round(_safe_float(row.get('changepercent', 0)), 2),
                        'unit': '%'
                    },
                    'volume': {
                        'value': round(_safe_float(row.get('volume', 0)) / 100000000, 2),
                        'unit': '亿股'
                    },
                    'amount': {
                        'value': round(_safe_float(row.get('amount', 0)) / 100000000, 2),
                        'unit': '亿元'
                    },
                    'errors': None
                }
    except Exception as e:
        errors.append(f"新浪接口失败: {e}")
    
    return _error_response(code, errors)


def get_valuation_data_json(code: str) -> str:
    """返回 JSON 格式的估值数据"""
    data = get_valuation_data(code)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _safe_float(value) -> float:
    """安全转换为浮点数"""
    if pd.isna(value):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _error_response(code: str, errors: List[str]) -> Dict[str, Any]:
    """错误响应"""
    return {
        'code': code,
        'name': '',
        'source': 'AkShare',
        'fetched_at': datetime.now().isoformat(),
        'price': {'value': 0, 'unit': '元'},
        'pe_ttm': {'value': None, 'unit': '倍'},
        'pb': {'value': None, 'unit': '倍'},
        'market_cap': {'value': None, 'unit': '亿元'},
        'circulating_market_cap': {'value': None, 'unit': '亿元'},
        'change_percent': {'value': None, 'unit': '%'},
        'volume': {'value': None, 'unit': '亿股'},
        'amount': {'value': None, 'unit': '亿元'},
        'errors': errors
    }


# 测试入口
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    
    # 测试迈瑞医疗
    print("=== 测试迈瑞医疗 300760 ===")
    result = get_valuation_data("300760")
    print(json.dumps(result, ensure_ascii=False, indent=2))