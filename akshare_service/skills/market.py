"""
行情相关能力 (Market Skills)
提供 A股、港股、美股的实时行情和历史K线数据。
数据源优先级：Longbridge → AkShare(东财) → AkShare(新浪)
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import sys

sys.path.insert(0, '/root/.openclaw/workspace/Longbridge_tools/src')

from akshare_service.infra.client import robust_api


def _get_longbridge_quote_skill():
    """获取 Longbridge QuoteSkill 实例"""
    try:
        from longbridge_tools import QuoteSkill
        from longbridge_tools.config import AppConfig
        
        # 尝试加载配置
        config_path = '/root/.openclaw/workspace/Longbridge_tools/config.yaml'
        config = AppConfig.load(config_path)
        return QuoteSkill(config)
    except Exception as e:
        print(f"Longbridge 初始化失败: {e}")
        return None


def _convert_code_to_longbridge(market: str, code: str) -> str:
    """转换股票代码为 Longbridge 格式"""
    if market == 'A股':
        # 300760 -> 300760.SH
        if code.startswith('6'):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"
    elif market == '港股':
        # 00700 -> 700.HK
        return f"{int(code)}.HK"
    elif market == '美股':
        # AAPL -> AAPL.US
        return f"{code}.US"
    return code


@robust_api
def get_current_price(market: str, code: str) -> Dict[str, Any]:
    """
    获取股票当前实时行情 (支持多源 Fallback)
    数据源优先级：Longbridge → AkShare(东财)
    """
    errors = []
    
    # === 1. 尝试 Longbridge ===
    try:
        quote_skill = _get_longbridge_quote_skill()
        if quote_skill:
            lb_code = _convert_code_to_longbridge(market, code)
            quotes = quote_skill.get_quote([lb_code])
            if quotes:
                q = quotes[0]
                return {
                    'code': code,
                    'name': q.name if hasattr(q, 'name') else '',
                    'price': float(q.last_done) if hasattr(q, 'last_done') else 0,
                    'change_percent': float(q.change_rate * 100) if hasattr(q, 'change_rate') else 0,
                    'volume': float(q.volume) if hasattr(q, 'volume') else 0,
                    'amount': float(q.turnover) if hasattr(q, 'turnover') else 0,
                    'time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    'source': 'Longbridge'
                }
    except Exception as e:
        errors.append(f"Longbridge failed: {e}")
    
    # === 2. 尝试 AkShare (东财) ===
    if market == 'A股':
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                stock = df[df['代码'] == code]
                if not stock.empty:
                    row = stock.iloc[0]
                    return {
                        'code': str(row['代码']),
                        'name': str(row['名称']),
                        'price': float(row['最新价']),
                        'change_percent': float(row['涨跌幅']),
                        'volume': float(row['成交量']),
                        'amount': float(row['成交额']),
                        'market_value': float(row['总市值']),
                        'pe': float(row['市盈率-动态']),
                        'pb': float(row['市净率']),
                        'time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                        'source': 'AkShare.东财'
                    }
        except Exception as e:
            errors.append(f"AkShare failed: {e}")

    elif market == '港股':
        try:
            df = ak.stock_hk_spot_em()
            if df is not None and not df.empty:
                stock = df[df['代码'] == code]
                if not stock.empty:
                    row = stock.iloc[0]
                    return {
                        'code': str(row['代码']),
                        'name': str(row['名称']),
                        'price': float(row['最新价']),
                        'change_percent': float(row['涨跌幅']),
                        'volume': float(row['成交量']),
                        'amount': float(row['成交额']),
                        'time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                        'source': 'AkShare.东财'
                    }
        except Exception as e:
            errors.append(f"AkShare failed: {e}")

    elif market == '美股':
        try:
            df = ak.stock_us_spot_em()
            if df is not None and not df.empty:
                stock = df[df['代码'] == code]
                if not stock.empty:
                    row = stock.iloc[0]
                    return {
                        'code': str(row['代码']),
                        'name': str(row['名称']),
                        'price': float(row['最新价']),
                        'change_percent': float(row['涨跌幅']),
                        'volume': float(row['成交量']),
                        'amount': float(row['成交额']),
                        'time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                        'source': 'AkShare.东财'
                    }
        except Exception as e:
            errors.append(f"AkShare failed: {e}")

    return {'error': f"All sources failed. Errors: {'; '.join(errors)}"}

@robust_api
def get_history_price(market: str, code: str, start_date: str = '20240101', end_date: str = '20500101', adjust: str = "qfq") -> pd.DataFrame:
    """
    获取历史K线数据 (支持多源 Fallback)
    数据源优先级：Longbridge → AkShare(东财) → AkShare(新浪)
    """
    errors = []
    df = pd.DataFrame()
    
    # === 1. 尝试 Longbridge ===
    try:
        quote_skill = _get_longbridge_quote_skill()
        if quote_skill:
            lb_code = _convert_code_to_longbridge(market, code)
            adjust_type = "forward_adjust" if adjust == "qfq" else "no_adjust"
            candlesticks = quote_skill.get_candlesticks(lb_code, "day", 500, adjust_type)
            
            if candlesticks:
                data = []
                for cs in candlesticks:
                    # 处理时间戳
                    import time
                    if hasattr(cs.timestamp, 'timestamp'):
                        ts = int(cs.timestamp.timestamp())
                    else:
                        ts = int(cs.timestamp)
                    
                    data.append({
                        'date': time.strftime('%Y-%m-%d', time.localtime(ts)),
                        'open': float(cs.open),
                        'close': float(cs.close),
                        'high': float(cs.high),
                        'low': float(cs.low),
                        'volume': float(cs.volume),
                        'amount': float(cs.turnover) if hasattr(cs, 'turnover') else 0
                    })
                df = pd.DataFrame(data)
                
                # 过滤日期
                df['date'] = pd.to_datetime(df['date'])
                mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
                df = df.loc[mask]
                df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                df['source'] = 'Longbridge'
                return df
    except Exception as e:
        errors.append(f"Longbridge failed: {e}")
    
    # === 2. 尝试 AkShare (东财/新浪) ===
    if market == 'A股':
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
            if df is not None and not df.empty:
                rename_map = {
                    '日期': 'date', '开盘': 'open', '收盘': 'close', 
                    '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'
                }
                df = df.rename(columns=rename_map)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                df['source'] = 'AkShare'
                return df
        except Exception as e:
            errors.append(f"AkShare failed: {e}")

    elif market == '港股':
        try:
            df = ak.stock_hk_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
            if df is not None and not df.empty:
                rename_map = {
                    '日期': 'date', '开盘': 'open', '收盘': 'close', 
                    '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'
                }
                df = df.rename(columns=rename_map)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                df['source'] = 'AkShare'
                return df
        except Exception as e:
            errors.append(f"AkShare failed: {e}")

    elif market == '美股':
        try:
            df = ak.stock_us_daily(symbol=code, adjust=adjust)
            if df is not None and not df.empty:
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
                    df = df.loc[mask]
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                    df['source'] = 'AkShare'
                    return df
        except Exception as e:
            errors.append(f"AkShare failed: {e}")

    if df.empty:
        print(f"Failed to get history for {code}. Errors: {'; '.join(errors)}")
        
    return df
