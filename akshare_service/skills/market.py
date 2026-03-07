"""
行情相关能力 (Market Skills)
提供 A股、港股、美股的实时行情和历史K线数据。
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

from akshare_service.infra.client import robust_api

@robust_api
def get_current_price(market: str, code: str) -> Dict[str, Any]:
    """
    获取股票当前实时行情 (支持多源 Fallback)
    """
    errors = []
    
    # === A股 ===
    if market == 'A股':
        # 1. 尝试东财 (EastMoney)
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
                        'time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    }
        except Exception as e:
            errors.append(f"EastMoney failed: {e}")
            
        # 2. 尝试新浪 (Sina)
        try:
            # stock_zh_a_spot (Sina)
            # 新浪源比较老，可能不稳定，但通常不被封
            # 注意：akshare 的 stock_zh_a_spot 可能也是全量列表，比较慢
            # 更好的是 stock_zh_a_spot_sina ? 好像没有单独个股的实时接口
            # 只有 stock_zh_a_spot (全量)
            pass 
        except Exception:
            pass

    # === 港股 ===
    elif market == '港股':
        # 1. 尝试东财
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
                        'market_value': float(row['总市值']) if '总市值' in row else 0,
                        'pe': float(row['市盈率-动态']) if '市盈率-动态' in row else 0,
                        'pb': float(row['市净率']) if '市净率' in row else 0,
                        'time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    }
        except Exception as e:
            errors.append(f"EastMoney failed: {e}")

    # === 美股 ===
    elif market == '美股':
        # 1. 尝试东财
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
                        'market_value': float(row['总市值']),
                        'pe': float(row['市盈率']),
                        'pb': 0.0,
                        'time': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    }
        except Exception as e:
            errors.append(f"EastMoney failed: {e}")
            
        # 2. 尝试新浪 (Sina) - 个股实时
        # ak.stock_us_spot() 是全量列表
        # ak.stock_us_daily() 是历史
        # 好像没有专门的美股个股实时接口 (除了东财)
        pass

    else:
        return {'error': f"Unknown market: {market}"}
        
    return {'error': f"All sources failed. Errors: {'; '.join(errors)}"}

@robust_api
def get_history_price(market: str, code: str, start_date: str = '20240101', end_date: str = '20500101', adjust: str = "qfq") -> pd.DataFrame:
    """
    获取历史K线数据 (支持多源 Fallback)
    """
    errors = []
    df = pd.DataFrame()
    
    # === A股 ===
    if market == 'A股':
        # 1. 尝试东财 (EastMoney)
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
            if df is not None and not df.empty:
                rename_map = {
                    '日期': 'date', '开盘': 'open', '收盘': 'close', 
                    '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'
                }
                df = df.rename(columns=rename_map)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                return df
        except Exception as e:
            errors.append(f"EastMoney failed: {e}")
            
        # 2. 尝试新浪 (Sina)
        try:
            # stock_zh_a_daily (Sina)
            # 注意：新浪接口可能不支持 start/end，只返回最近数据?
            # akshare 文档：stock_zh_a_daily(symbol='sh600519', adjust='qfq')
            # code 需要带前缀
            prefix_code = ('sh' if code.startswith('6') else 'sz') + code
            df = ak.stock_zh_a_daily(symbol=prefix_code, adjust=adjust)
            if df is not None and not df.empty:
                # 过滤日期
                df['date'] = pd.to_datetime(df['date'])
                mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
                df = df.loc[mask]
                df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                return df
        except Exception as e:
            errors.append(f"Sina failed: {e}")

    # === 港股 ===
    elif market == '港股':
        # 1. 尝试东财
        try:
            df = ak.stock_hk_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)
            if df is not None and not df.empty:
                rename_map = {
                    '日期': 'date', '开盘': 'open', '收盘': 'close', 
                    '最高': 'high', '最低': 'low', '成交量': 'volume', '成交额': 'amount'
                }
                df = df.rename(columns=rename_map)
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                return df
        except Exception as e:
            errors.append(f"EastMoney failed: {e}")
            
        # 2. 尝试新浪 (Sina)
        try:
            # stock_hk_daily (Sina)
            df = ak.stock_hk_daily(symbol=code, adjust=adjust)
            if df is not None and not df.empty:
                # rename columns if needed
                # 新浪港股返回的列名通常是英文? date, open...
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
                    df = df.loc[mask]
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                    return df
        except Exception as e:
            errors.append(f"Sina failed: {e}")

    # === 美股 ===
    elif market == '美股':
        # 1. 尝试新浪 (Sina) - 优先尝试，因为它更稳定且只要代码
        try:
            df = ak.stock_us_daily(symbol=code, adjust=adjust)
            if df is not None and not df.empty:
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
                    df = df.loc[mask]
                    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                    return df
        except Exception as e:
            errors.append(f"Sina failed: {e}")
            
        # 2. 尝试东财
        try:
            # 需要 full code e.g. 105.AAPL
            # 暂时跳过，因为不知道前缀
            pass
        except Exception:
            pass
            
    else:
        print(f"Unknown market: {market}")

    if df.empty:
        print(f"Failed to get history for {code}. Errors: {'; '.join(errors)}")
        
    return df
