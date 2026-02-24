"""
ROIC 计算工具
用于计算 A股、港股、美股的 ROIC（投入资本回报率）

计算公式：
投入资本 = 股东权益 + 有息负债 - 现金及等价物
ROIC = NOPAT / 投入资本 × 100%
NOPAT = 营业利润 × (1 - 税率)
税率 = 所得税费用 / 利润总额

Author: 小叶
Date: 2026-02-24
"""

import akshare as ak
import pandas as pd


def calculate_roic_a_share(symbol, years=5):
    """
    计算 A股 ROIC
    
    Args:
        symbol: 股票代码，如 'SH600519'
        years: 年数，默认 5
    
    Returns:
        DataFrame: 包含 ROIC 等数据的数据框
    """
    # 获取利润表
    df_profit = ak.stock_profit_sheet_by_yearly_em(symbol=symbol)
    df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])
    
    # 获取资产负债表
    df_balance = ak.stock_balance_sheet_by_yearly_em(symbol=symbol)
    df_balance['REPORT_DATE'] = pd.to_datetime(df_balance['REPORT_DATE'])
    
    # 筛选最近 N 年
    latest_years = sorted(df_profit['REPORT_DATE'].dt.year.unique())[-years:]
    results = []
    
    for year in latest_years:
        profit_row = df_profit[df_profit['REPORT_DATE'].dt.year == year].iloc[0]
        balance_row = df_balance[df_balance['REPORT_DATE'].dt.year == year].iloc[0]
        
        # 分子：NOPAT
        # ⚠️ 关键：必须用 OPERATE_PROFIT，不是 OPERATE_INCOME
        operate_profit = profit_row.get('OPERATE_PROFIT', 0)
        total_profit = profit_row.get('TOTAL_PROFIT', 0)
        income_tax = profit_row.get('INCOME_TAX', 0)
        
        # 计算税率（基于利润总额）
        if pd.notna(total_profit) and total_profit > 0 and pd.notna(income_tax):
            tax_rate = income_tax / total_profit
            nopat = operate_profit * (1 - tax_rate)
        else:
            nopat = operate_profit
            tax_rate = 0
        
        # 分母：投入资本
        # ⚠️ 关键：必须用 MONETARYFUNDS（货币资金），不是现金流量表的 END_CASH_EQUIVALENTS
        shareholder_equity = balance_row.get('TOTAL_EQUITY', 0)
        monetary_funds = balance_row.get('MONETARYFUNDS', 0)
        
        # 有息负债
        short_loan = balance_row.get('SHORT_LOAN', 0)
        long_loan = balance_row.get('LONG_LOAN', 0)
        noncurrent_liab_1year = balance_row.get('NONCURRENT_LIAB_1YEAR', 0)
        
        interest_bearing_debt = (
            (short_loan if pd.notna(short_loan) else 0) +
            (long_loan if pd.notna(long_loan) else 0) +
            (noncurrent_liab_1year if pd.notna(noncurrent_liab_1year) else 0)
        )
        
        invested_capital = shareholder_equity + interest_bearing_debt - monetary_funds
        
        # ROIC
        if invested_capital > 0:
            roic = (nopat / invested_capital) * 100
        else:
            roic = 0
        
        # 净利润和营业收入
        net_profit = profit_row.get('NETPROFIT', 0)
        total_operate_income = profit_row.get('TOTAL_OPERATE_INCOME', 0)
        
        results.append({
            '年份': year,
            'ROIC': roic,
            'NOPAT': nopat / 100000000,
            '投入资本': invested_capital / 100000000,
            '营业利润': operate_profit / 100000000,
            '利润总额': total_profit / 100000000,
            '所得税费用': income_tax / 100000000,
            '税率': tax_rate,
            '营业总收入': total_operate_income / 100000000,
            '净利润': net_profit / 100000000,
            '股东权益': shareholder_equity / 100000000,
            '有息负债': interest_bearing_debt / 100000000,
            '货币资金': monetary_funds / 100000000,
            '计算方法': f"营业利润×(1-税率{tax_rate:.2%})"
        })
    
    return pd.DataFrame(results).sort_values('年份')


def calculate_roic_hk(stock, years=5):
    """
    计算港股 ROIC
    
    Args:
        stock: 股票代码，如 '00700'
        years: 年数，默认 5
    
    Returns:
        DataFrame: 包含 ROIC 等数据的数据框
    """
    # 获取利润表
    df_profit = ak.stock_financial_hk_report_em(stock=stock, symbol='利润表', indicator='年度')
    df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])
    
    # 获取资产负债表
    df_balance = ak.stock_financial_hk_report_em(stock=stock, symbol='资产负债表', indicator='年度')
    df_balance['REPORT_DATE'] = pd.to_datetime(df_balance['REPORT_DATE'])
    
    # 透视转换
    profit_pivot = df_profit.pivot(index='REPORT_DATE', columns='STD_ITEM_NAME', values='AMOUNT').reset_index()
    balance_pivot = df_balance.pivot(index='REPORT_DATE', columns='STD_ITEM_NAME', values='AMOUNT').reset_index()
    
    # 筛选最近 N 年
    latest_years = sorted(profit_pivot['REPORT_DATE'].dt.year.unique())[-years:]
    results = []
    
    for year in latest_years:
        profit_row = profit_pivot[profit_pivot['REPORT_DATE'].dt.year == year].iloc[0]
        balance_row = balance_pivot[balance_pivot['REPORT_DATE'].dt.year == year].iloc[0]
        
        # 分子：NOPAT
        # ⚠️ 关键：港股用"经营溢利"，不是"营业利润"
        operate_profit = profit_row.get('经营溢利', 0)
        profit_before_tax = profit_row.get('除税前溢利', 0)
        income_tax = profit_row.get('税项', 0)
        
        # 计算税率（基于税前利润）
        if pd.notna(profit_before_tax) and profit_before_tax > 0 and pd.notna(income_tax):
            tax_rate = income_tax / profit_before_tax
            nopat = operate_profit * (1 - tax_rate)
        else:
            nopat = operate_profit
            tax_rate = 0
        
        # 分母：投入资本
        shareholder_equity = balance_row.get('股东权益', 0)
        cash = balance_row.get('现金及等价物', 0)
        
        # 有息负债
        # ⚠️ 关键：港股用"贷款"不是"借款"
        short_term_borrowing = balance_row.get('短期贷款', 0)  # 短期借款
        long_term_borrowing = balance_row.get('长期贷款', 0)  # 长期借款
        bonds_payable = balance_row.get('应付票据(非流动)', 0)  # 应付债券
        finance_lease_liability = (
            balance_row.get('融资租赁负债(流动)', 0) + 
            balance_row.get('融资租赁负债(非流动)', 0)
        )  # 融资租赁负债
        
        interest_bearing_debt = (
            (short_term_borrowing if pd.notna(short_term_borrowing) else 0) +
            (long_term_borrowing if pd.notna(long_term_borrowing) else 0) +
            (bonds_payable if pd.notna(bonds_payable) else 0) +
            (finance_lease_liability if pd.notna(finance_lease_liability) else 0)
        )
        
        invested_capital = shareholder_equity + interest_bearing_debt - cash
        
        # ROIC
        if invested_capital > 0:
            roic = (nopat / invested_capital) * 100
        else:
            roic = 0
        
        # 净利润和营业收入
        net_profit = profit_row.get('股东应占溢利', 0)
        operating_revenue = profit_row.get('营运收入', 0)
        
        results.append({
            '年份': year,
            'ROIC': roic,
            'NOPAT': nopat / 100000000,
            '投入资本': invested_capital / 100000000,
            '营业利润': operate_profit / 100000000,
            '利润总额': profit_before_tax / 100000000,
            '所得税费用': income_tax / 100000000,
            '税率': tax_rate,
            '营业收入': operating_revenue / 100000000,
            '净利润': net_profit / 100000000,
            '股东权益': shareholder_equity / 100000000,
            '有息负债': interest_bearing_debt / 100000000,
            '现金及等价物': cash / 100000000,
            '计算方法': f"营业利润×(1-税率{tax_rate:.2%})"
        })
    
    return pd.DataFrame(results).sort_values('年份')


def calculate_roic_us(stock, years=5):
    """
    计算美股 ROIC
    
    Args:
        stock: 股票代码，如 'PDD'
        years: 年数，默认 5
    
    Returns:
        DataFrame: 包含 ROIC 等数据的数据框
    """
    # 获取利润表（综合损益表）
    # ⚠️ 关键：symbol 必须用中文"综合损益表"，不是"利润表"
    df_profit = ak.stock_financial_us_report_em(stock=stock, symbol='综合损益表', indicator='年报')
    df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])
    
    # 获取资产负债表
    df_balance = ak.stock_financial_us_report_em(stock=stock, symbol='资产负债表', indicator='年报')
    df_balance['REPORT_DATE'] = pd.to_datetime(df_balance['REPORT_DATE'])
    
    # 透视转换
    profit_pivot = df_profit.pivot(index='REPORT_DATE', columns='ITEM_NAME', values='AMOUNT').reset_index()
    balance_pivot = df_balance.pivot(index='REPORT_DATE', columns='ITEM_NAME', values='AMOUNT').reset_index()
    
    # 筛选最近 N 年
    latest_years = sorted(profit_pivot['REPORT_DATE'].dt.year.unique())[-years:]
    results = []
    
    for year in latest_years:
        profit_row = profit_pivot[profit_pivot['REPORT_DATE'].dt.year == year].iloc[0]
        balance_row = balance_pivot[balance_pivot['REPORT_DATE'].dt.year == year].iloc[0]
        
        # 分子：NOPAT
        # ⚠️ 关键：支持中英文字段名
        operating_income = profit_row.get('Operating income') or profit_row.get('营业利润') or 0
        income_before_tax = profit_row.get('Income before tax') or profit_row.get('持续经营税前利润') or 0
        income_tax = profit_row.get('Income tax expense') or profit_row.get('所得税') or 0
        
        # 计算税率（基于税前利润）
        if pd.notna(income_before_tax) and income_before_tax > 0 and pd.notna(income_tax):
            tax_rate = income_tax / income_before_tax
            nopat = operating_income * (1 - tax_rate)
        else:
            nopat = operating_income
            tax_rate = 0
        
        # 分母：投入资本
        # ⚠️ 关键：支持中英文字段名
        stockholders_equity = (
            balance_row.get('股东权益合计') or 
            balance_row.get('归属于母公司股东权益') or 
            balance_row.get('Stockholders\' equity') or 0
        )
        cash = balance_row.get('现金及现金等价物') or balance_row.get('Cash and cash equivalents') or 0
        
        # 有息负债
        short_term_debt = balance_row.get('短期债务') or balance_row.get('Short-term debt') or 0
        long_term_debt = balance_row.get('长期负债') or balance_row.get('Long-term debt') or 0
        convertible_bonds = balance_row.get('可转换票据及债券') or 0
        capital_lease_debt = (
            balance_row.get('资本租赁债务(流动)', 0) + 
            balance_row.get('资本租赁债务(非流动)', 0)
        )
        
        interest_bearing_debt = (
            (short_term_debt if pd.notna(short_term_debt) else 0) +
            (long_term_debt if pd.notna(long_term_debt) else 0) +
            (convertible_bonds if pd.notna(convertible_bonds) else 0) +
            (capital_lease_debt if pd.notna(capital_lease_debt) else 0)
        )
        
        invested_capital = stockholders_equity + interest_bearing_debt - cash
        
        # ROIC
        if invested_capital > 0:
            roic = (nopat / invested_capital) * 100
        else:
            roic = 0
        
        # 净利润和营业收入
        net_income = profit_row.get('Net income') or profit_row.get('净利润') or 0
        total_revenue = (
            profit_row.get('Total revenue') or 
            profit_row.get('营业收入') or 
            profit_row.get('主营收入') or 0
        )
        
        results.append({
            '年份': year,
            'ROIC': roic,
            'NOPAT': nopat / 100000000,
            '投入资本': invested_capital / 100000000,
            '营业利润': operating_income / 100000000,
            '税前利润': income_before_tax / 100000000,
            '所得税费用': income_tax / 100000000,
            '税率': tax_rate,
            '营业收入': total_revenue / 100000000,
            '净利润': net_income / 100000000,
            '股东权益': stockholders_equity / 100000000,
            '有息负债': interest_bearing_debt / 100000000,
            '现金及等价物': cash / 100000000,
            '计算方法': f"营业利润×(1-税率{tax_rate:.2%})"
        })
    
    return pd.DataFrame(results).sort_values('年份')


def calculate_roic(market, code, years=5):
    """
    统一的 ROIC 计算入口
    
    Args:
        market: 市场类型，'A股'、'港股' 或 '美股'
        code: 股票代码
        years: 年数，默认 5
    
    Returns:
        DataFrame: 包含 ROIC 等数据的数据框
    
    Examples:
        >>> df = calculate_roic('A股', 'SH600519')
        >>> df = calculate_roic('港股', '00700')
        >>> df = calculate_roic('美股', 'PDD')
    """
    if market == 'A股':
        return calculate_roic_a_share(code, years)
    elif market == '港股':
        return calculate_roic_hk(code, years)
    elif market == '美股':
        return calculate_roic_us(code, years)
    else:
        raise ValueError(f"不支持的市场类型：{market}，请选择 'A股'、'港股' 或 '美股'")


if __name__ == '__main__':
    # 设置显示选项
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    print("=" * 140)
    print("🍷 贵州茅台（A股：SH600519）")
    print("=" * 140)
    df_moutai = calculate_roic_a_share('SH600519', years=5)
    print(df_moutai.to_string(index=False))
    print()
    
    print("=" * 140)
    print("🐧 腾讯控股（港股：00700）")
    print("=" * 140)
    df_tencent = calculate_roic_hk('00700', years=5)
    print(df_tencent.to_string(index=False))
    print()
    
    print("=" * 140)
    print("🛒 PDD（美股：PDD）")
    print("=" * 140)
    df_pdd = calculate_roic_us('PDD', years=5)
    print(df_pdd.to_string(index=False))
    print()