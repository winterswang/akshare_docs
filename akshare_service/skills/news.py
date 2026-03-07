"""
新闻资讯能力 (News Skills)
提供个股新闻、公告等资讯获取能力。
"""

import akshare as ak
import pandas as pd
from typing import List, Dict, Any
import os

from akshare_service.infra.client import robust_api

@robust_api
def get_stock_news(market: str, code: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    获取个股新闻资讯
    """
    # 临时清除代理，防止 ProxyError
    if os.environ.get('http_proxy') or os.environ.get('https_proxy'):
        print("Warning: Proxy detected, this might cause issues with AkShare.")
        # del os.environ['http_proxy']
        # del os.environ['https_proxy']

    news_list = []
    try:
        if market == 'A股':
            # stock_news_em (东财)
            df = ak.stock_news_em(symbol=code)
            
            if df is None or df.empty:
                return []
                
            # Check columns
            if '标题' not in df.columns:
                # Check if column names are different
                if '新闻标题' in df.columns:
                    df = df.rename(columns={
                        '新闻标题': '标题',
                        '新闻链接': '链接',
                        '新闻内容': '内容'
                    })
                else:
                    print(f"Unexpected columns in stock_news_em: {df.columns.tolist()}")
                    return []
                
            # columns: 关键词, 类型, 标题, 链接, 发布时间, 文章来源
            if '发布时间' in df.columns:
                df = df.sort_values('发布时间', ascending=False)
            
            df = df.head(limit)
            
            for _, row in df.iterrows():
                news_list.append({
                    'title': row.get('标题', ''),
                    'publish_time': row.get('发布时间', ''),
                    'url': row.get('链接', ''),
                    'source': row.get('文章来源', '')
                })
                
        elif market == '港股':
            pass
            
        elif market == '美股':
            pass
            
    except Exception as e:
        print(f"Error fetching news for {code}: {e}")
        
    return news_list

@robust_api
def get_market_news(limit: int = 20) -> List[Dict[str, Any]]:
    """
    获取市场综合财经新闻 (东财)
    """
    try:
        # 尝试不同的接口，因为 akshare 版本差异
        # 1. 财联社电报
        try:
            df = ak.stock_telegraph_cls()
        except AttributeError:
            # 兼容旧版本或接口更名
            try:
                df = ak.stock_info_global_cls(symbol="财经")
            except:
                # 尝试东财财经
                try:
                    df = ak.stock_news_main_cx() # 财新
                except:
                    return []
        
        if df is None or df.empty:
            return []
            
        df = df.head(limit)
        
        news = []
        for _, row in df.iterrows():
            # 兼容不同接口的列名
            title = row.get('标题') or row.get('新闻标题') or row.get('title')
            content = row.get('内容') or row.get('新闻内容') or row.get('content') or ''
            
            if not title and content:
                title = content[:30]
                
            news.append({
                'title': title,
                'content': content,
                'publish_time': f"{row.get('日期','')} {row.get('时间','')}".strip() or row.get('发布时间', ''),
                'url': row.get('链接') or row.get('新闻链接') or row.get('url') or ''
            })
        return news
    except Exception as e:
        print(f"Error fetching market news: {e}")
        return []
