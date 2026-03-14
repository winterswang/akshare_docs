"""
新闻资讯能力 (News Skills)
提供个股新闻、公告等资讯获取能力。
数据源优先级：AkShare(东财) → Tavily/Exa(兜底)
"""

import akshare as ak
import pandas as pd
from typing import List, Dict, Any
import os
import sys

sys.path.insert(0, '/root/.openclaw/workspace/deer-flow-analysis/backend')

from akshare_service.infra.client import robust_api


def _get_stock_news_tavily(code: str, stock_name: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """使用 Tavily 搜索股票新闻（兜底方案）"""
    try:
        from tavily import TavilyClient
        import os
        
        api_key = os.environ.get('TAVILY_API_KEY')
        if not api_key:
            return []
        
        client = TavilyClient(api_key=api_key)
        
        # 搜索关键词
        query = f"{stock_name} {code} 股票 新闻" if stock_name else f"{code} 股票 新闻"
        
        result = client.search(query, max_results=limit)
        
        news_list = []
        for item in result.get('results', []):
            news_list.append({
                'title': item.get('title', ''),
                'publish_time': item.get('published_date', ''),
                'url': item.get('url', ''),
                'source': item.get('source', ''),
                'content': item.get('content', '')[:200] if item.get('content') else ''
            })
        
        return news_list
    except Exception as e:
        print(f"Tavily 搜索失败: {e}")
        return []


@robust_api
def get_stock_news(market: str, code: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    获取个股新闻资讯
    数据源优先级：AkShare(东财) → Tavily(兜底)
    """
    news_list = []
    
    # === 1. 尝试 AkShare (东财) ===
    try:
        if market == 'A股':
            df = ak.stock_news_em(symbol=code)
            
            if df is not None and not df.empty:
                if '标题' not in df.columns:
                    if '新闻标题' in df.columns:
                        df = df.rename(columns={
                            '新闻标题': '标题',
                            '新闻链接': '链接',
                            '新闻内容': '内容'
                        })
                    else:
                        print(f"Unexpected columns: {df.columns.tolist()}")
                        df = None
                
                if df is not None and '发布时间' in df.columns:
                    df = df.sort_values('发布时间', ascending=False)
                
                if df is not None:
                    df = df.head(limit)
                    for _, row in df.iterrows():
                        news_list.append({
                            'title': row.get('标题', ''),
                            'publish_time': row.get('发布时间', ''),
                            'url': row.get('链接', ''),
                            'source': row.get('文章来源', ''),
                            'data_source': 'AkShare'
                        })
    except Exception as e:
        print(f"AkShare 获取新闻失败: {e}")
    
    # === 2. 如果 AkShare 失败，尝试 Tavily ===
    if not news_list:
        print("尝试 Tavily 兜底...")
        stock_name = ""
        # 尝试获取股票名称
        try:
            if market == 'A股':
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    stock = df[df['代码'] == code]
                    if not stock.empty:
                        stock_name = stock.iloc[0]['名称']
        except:
            pass
        
        news_list = _get_stock_news_tavily(code, stock_name, limit)
        for news in news_list:
            news['data_source'] = 'Tavily'
        
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
