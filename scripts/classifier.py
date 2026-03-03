#!/usr/bin/env python3
"""
接口分类器

根据 API 名称自动分类
"""

from typing import Dict, List


# 分类规则：关键词 -> 分类
CATEGORY_RULES = {
    'stock': [
        'stock_', 'equity', 'a_stock', 'zh_a', 'bj_a', 'sh_a', 'sz_a',
        'stock', 'ticker', 'quote', 'kline', 'hist'
    ],
    'fund': [
        'fund_', 'etf', 'fund', 'open_fund', 'private_fund'
    ],
    'bond': [
        'bond_', 'bond', 'treasury', 'debenture'
    ],
    'futures': [
        'futures_', 'fut_', 'option_', 'commodity_', 'forward_'
    ],
    'forex': [
        'fx_', 'forex', 'currency_', 'exchange_rate'
    ],
    'crypto': [
        'crypto_', 'btc', 'eth', 'bitcoin', 'ethereum', 'coin_'
    ],
    'macro': [
        'macro_', 'economy_', 'gdp', 'cpi', 'ppi', 'm1', 'm2'
    ],
    'news': [
        'news_', 'notice_', 'announcement_', 'report_'
    ],
    'index': [
        'index_', 'indices'
    ],
    'money': [
        'money_', 'shibor', 'libor', 'hibor', 'repo'
    ],
    'energy': [
        'energy_', 'oil_', 'gas_', 'coal_'
    ],
}


def classify_api(api_name: str) -> str:
    """
    根据API名称分类
    
    Args:
        api_name: API 名称
        
    Returns:
        分类名称
    """
    api_lower = api_name.lower()
    
    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword in api_lower:
                return category
    
    return 'other'


def classify_apis(api_names: List[str]) -> Dict[str, List[str]]:
    """
    批量分类 API
    
    Args:
        api_names: API 名称列表
        
    Returns:
        分类 -> API 列表的字典
    """
    result = {}
    
    for api_name in api_names:
        category = classify_api(api_name)
        if category not in result:
            result[category] = []
        result[category].append(api_name)
    
    return result


def get_category_description(category: str) -> str:
    """获取分类描述"""
    descriptions = {
        'stock': '股票 - A股/港股/美股行情、财报',
        'fund': '基金 - 公募/私募基金数据',
        'bond': '债券 - 国债/企业债数据',
        'futures': '期货 - 商品/金融期货',
        'forex': '外汇 - 汇率数据',
        'crypto': '数字货币 - 加密货币行情',
        'macro': '宏观经济 - 经济指标',
        'news': '新闻公告 - 资讯信息',
        'index': '指数 - 各类指数数据',
        'money': '货币市场 - 利率、回购等',
        'energy': '能源 - 油气煤炭等',
        'other': '其他 - 未分类接口'
    }
    return descriptions.get(category, category)


if __name__ == '__main__':
    # 测试
    test_apis = [
        'stock_zh_a_hist',
        'fund_open_fund_info',
        'bond_zh_hs_cov_spot',
        'futures_main_sina',
        'fx_spot_quote',
        'crypto_hist',
        'macro_china_gdp',
        'news_report_time_baidu',
        'unknown_api'
    ]
    
    for api in test_apis:
        cat = classify_api(api)
        print(f"{api} -> {cat} ({get_category_description(cat)})")