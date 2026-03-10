"""
财务分析相关能力 (Finance Skills)
提供 ROIC 计算、利润表获取、资产负债表获取等财务分析功能。
"""

import akshare as ak
import pandas as pd
import os

from akshare_service.infra.client import robust_api

@robust_api
def calculate_roic_a_share(symbol: str, years: int = 5) -> pd.DataFrame:
    """
    计算 A股 ROIC (Return on Invested Capital)
    优先使用东方财富 API，失败时回退到新浪 API
    """
    # 尝试东方财富 API
    try:
        df_profit = ak.stock_profit_sheet_by_yearly_em(symbol=symbol)
        df_balance = ak.stock_balance_sheet_by_yearly_em(symbol=symbol)
        
        if df_profit is not None and not df_profit.empty and df_balance is not None and not df_balance.empty:
            df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])
            df_balance['REPORT_DATE'] = pd.to_datetime(df_balance['REPORT_DATE'])
            return _calculate_roic_from_em_data(df_profit, df_balance, years)
    except Exception as e:
        print(f"东方财富 API 失败，尝试新浪 API: {e}")
    
    # 回退到新浪 API
    try:
        # 构建股票代码（新浪格式：sh600519 或 sz000001）
        market = 'sh' if symbol.startswith('6') else 'sz'
        sina_code = f"{market}{symbol}"
        
        df_profit = ak.stock_financial_report_sina(stock=sina_code, symbol='利润表')
        df_balance = ak.stock_financial_report_sina(stock=sina_code, symbol='资产负债表')
        
        if df_profit is not None and not df_profit.empty and df_balance is not None and not df_balance.empty:
            return _calculate_roic_from_sina_data(df_profit, df_balance, years)
    except Exception as e:
        print(f"新浪 API 也失败: {e}")
    
    return pd.DataFrame()


def _calculate_roic_from_em_data(df_profit: pd.DataFrame, df_balance: pd.DataFrame, years: int) -> pd.DataFrame:
    """从东方财富数据计算 ROIC"""
    latest_years = sorted(df_profit['REPORT_DATE'].dt.year.unique())[-years:]
    results = []
    
    for year in latest_years:
        try:
            profit_row = df_profit[df_profit['REPORT_DATE'].dt.year == year].iloc[0]
            balance_row = df_balance[df_balance['REPORT_DATE'].dt.year == year].iloc[0]
            
            operate_profit = profit_row.get('OPERATE_PROFIT', 0)
            total_profit = profit_row.get('TOTAL_PROFIT', 0)
            income_tax = profit_row.get('INCOME_TAX', 0)
            
            if pd.notna(total_profit) and total_profit > 0 and pd.notna(income_tax):
                tax_rate = income_tax / total_profit
                nopat = operate_profit * (1 - tax_rate)
            else:
                nopat = operate_profit
                tax_rate = 0
            
            shareholder_equity = balance_row.get('TOTAL_EQUITY', 0)
            monetary_funds = balance_row.get('MONETARYFUNDS', 0)
            
            short_loan = balance_row.get('SHORT_LOAN', 0)
            long_loan = balance_row.get('LONG_LOAN', 0)
            noncurrent_liab_1year = balance_row.get('NONCURRENT_LIAB_1YEAR', 0)
            
            interest_bearing_debt = (
                (short_loan if pd.notna(short_loan) else 0) +
                (long_loan if pd.notna(long_loan) else 0) +
                (noncurrent_liab_1year if pd.notna(noncurrent_liab_1year) else 0)
            )
            
            invested_capital = shareholder_equity + interest_bearing_debt - monetary_funds
            
            if invested_capital > 0:
                roic = (nopat / invested_capital) * 100
            else:
                roic = 0
            
            net_profit = profit_row.get('NETPROFIT', 0)
            total_operate_income = profit_row.get('TOTAL_OPERATE_INCOME', 0)
            
            results.append({
                'year': year,
                'roic': round(roic, 2),
                'nopat': round(nopat / 100000000, 2),
                'invested_capital': round(invested_capital / 100000000, 2),
                'operate_profit': round(operate_profit / 100000000, 2),
                'tax_rate': round(tax_rate, 4),
                'net_profit': round(net_profit / 100000000, 2),
                'revenue': round(total_operate_income / 100000000, 2)
            })
        except (IndexError, KeyError):
            continue
    
    return pd.DataFrame(results).sort_values('year')


def _calculate_roic_from_sina_data(df_profit: pd.DataFrame, df_balance: pd.DataFrame, years: int) -> pd.DataFrame:
    """从新浪数据计算 ROIC"""
    # 新浪数据的日期列是 '报告日'
    df_profit['报告日'] = pd.to_datetime(df_profit['报告日'])
    df_balance['报告日'] = pd.to_datetime(df_balance['报告日'])
    
    # 筛选年报数据（12月31日）
    df_profit = df_profit[df_profit['报告日'].dt.month == 12]
    df_balance = df_balance[df_balance['报告日'].dt.month == 12]
    
    latest_years = sorted(df_profit['报告日'].dt.year.unique())[-years:]
    results = []
    
    for year in latest_years:
        try:
            profit_row = df_profit[df_profit['报告日'].dt.year == year].iloc[0]
            balance_row = df_balance[df_balance['报告日'].dt.year == year].iloc[0]
            
            # 营业利润
            operate_profit = profit_row.get('营业利润', 0)
            # 利润总额
            total_profit = profit_row.get('利润总额', 0)
            # 所得税
            income_tax = profit_row.get('所得税费用', 0)
            
            if pd.notna(total_profit) and total_profit > 0 and pd.notna(income_tax):
                tax_rate = income_tax / total_profit
                nopat = operate_profit * (1 - tax_rate)
            else:
                nopat = operate_profit
                tax_rate = 0
            
            # 股东权益合计
            shareholder_equity = balance_row.get('所有者权益(或股东权益)合计', 0)
            # 货币资金
            monetary_funds = balance_row.get('货币资金', 0)
            
            # 短期借款 + 长期借款
            short_loan = balance_row.get('短期借款', 0)
            long_loan = balance_row.get('长期借款', 0)
            
            interest_bearing_debt = (
                (short_loan if pd.notna(short_loan) else 0) +
                (long_loan if pd.notna(long_loan) else 0)
            )
            
            invested_capital = shareholder_equity + interest_bearing_debt - monetary_funds
            
            if invested_capital > 0:
                roic = (nopat / invested_capital) * 100
            else:
                roic = 0
            
            # 归属于母公司所有者的净利润
            net_profit = profit_row.get('归属于母公司所有者的净利润', 0)
            # 营业收入
            total_operate_income = profit_row.get('营业收入', 0)
            
            results.append({
                'year': year,
                'roic': round(roic, 2),
                'nopat': round(nopat / 100000000, 2) if pd.notna(nopat) else 0,
                'invested_capital': round(invested_capital / 100000000, 2) if pd.notna(invested_capital) else 0,
                'operate_profit': round(operate_profit / 100000000, 2) if pd.notna(operate_profit) else 0,
                'tax_rate': round(tax_rate, 4),
                'net_profit': round(net_profit / 100000000, 2) if pd.notna(net_profit) else 0,
                'revenue': round(total_operate_income / 100000000, 2) if pd.notna(total_operate_income) else 0
            })
        except (IndexError, KeyError) as e:
            print(f"Error processing year {year}: {e}")
            continue
    
    return pd.DataFrame(results).sort_values('year')


@robust_api
def calculate_roic_hk(stock: str, years: int = 5) -> pd.DataFrame:
    """
    计算港股 ROIC
    """
    try:
        # 获取利润表
        df_profit = ak.stock_financial_hk_report_em(stock=stock, symbol='利润表', indicator='年度')
        # 获取资产负债表
        df_balance = ak.stock_financial_hk_report_em(stock=stock, symbol='资产负债表', indicator='年度')
        
        if df_profit is None or df_profit.empty or df_balance is None or df_balance.empty:
            return pd.DataFrame()
            
        df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])
        df_balance['REPORT_DATE'] = pd.to_datetime(df_balance['REPORT_DATE'])
    except Exception as e:
        print(f"Error fetching HK financials for {stock}: {e}")
        return pd.DataFrame()
    
    # 透视转换
    profit_pivot = df_profit.pivot(index='REPORT_DATE', columns='STD_ITEM_NAME', values='AMOUNT').reset_index()
    balance_pivot = df_balance.pivot(index='REPORT_DATE', columns='STD_ITEM_NAME', values='AMOUNT').reset_index()
    
    # 筛选最近 N 年
    latest_years = sorted(profit_pivot['REPORT_DATE'].dt.year.unique())[-years:]
    results = []
    
    for year in latest_years:
        try:
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
            short_term_borrowing = balance_row.get('短期贷款', 0)
            long_term_borrowing = balance_row.get('长期贷款', 0)
            bonds_payable = balance_row.get('应付票据(非流动)', 0)
            finance_lease_liability = (
                balance_row.get('融资租赁负债(流动)', 0) + 
                balance_row.get('融资租赁负债(非流动)', 0)
            )
            
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
            
            net_profit = profit_row.get('股东应占溢利', 0)
            operating_revenue = profit_row.get('营运收入', 0)
            
            results.append({
                'year': year,
                'roic': round(roic, 2),
                'nopat': round(nopat / 100000000, 2),
                'invested_capital': round(invested_capital / 100000000, 2),
                'operate_profit': round(operate_profit / 100000000, 2),
                'tax_rate': round(tax_rate, 4),
                'net_profit': round(net_profit / 100000000, 2),
                'revenue': round(operating_revenue / 100000000, 2)
            })
        except IndexError:
            continue
    
    return pd.DataFrame(results).sort_values('year')


@robust_api
def calculate_roic_us(stock: str, years: int = 5) -> pd.DataFrame:
    """
    计算美股 ROIC
    """
    try:
        # 获取利润表（综合损益表）
        df_profit = ak.stock_financial_us_report_em(stock=stock, symbol='综合损益表', indicator='年报')
        # 获取资产负债表
        df_balance = ak.stock_financial_us_report_em(stock=stock, symbol='资产负债表', indicator='年报')
        
        if df_profit is None or df_profit.empty or df_balance is None or df_balance.empty:
            return pd.DataFrame()
            
        df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])
        df_balance['REPORT_DATE'] = pd.to_datetime(df_balance['REPORT_DATE'])
    except Exception as e:
        print(f"Error fetching US financials for {stock}: {e}")
        return pd.DataFrame()
    
    # 透视转换
    profit_pivot = df_profit.pivot(index='REPORT_DATE', columns='ITEM_NAME', values='AMOUNT').reset_index()
    balance_pivot = df_balance.pivot(index='REPORT_DATE', columns='ITEM_NAME', values='AMOUNT').reset_index()
    
    # 筛选最近 N 年
    latest_years = sorted(profit_pivot['REPORT_DATE'].dt.year.unique())[-years:]
    results = []
    
    for year in latest_years:
        try:
            profit_row = profit_pivot[profit_pivot['REPORT_DATE'].dt.year == year].iloc[0]
            balance_row = balance_pivot[balance_pivot['REPORT_DATE'].dt.year == year].iloc[0]
            
            # 分子：NOPAT
            operating_income = profit_row.get('Operating income') or profit_row.get('营业利润') or 0
            income_before_tax = profit_row.get('Income before tax') or profit_row.get('持续经营税前利润') or 0
            income_tax = profit_row.get('Income tax expense') or profit_row.get('所得税') or 0
            
            # 计算税率
            if pd.notna(income_before_tax) and income_before_tax > 0 and pd.notna(income_tax):
                tax_rate = income_tax / income_before_tax
                nopat = operating_income * (1 - tax_rate)
            else:
                nopat = operating_income
                tax_rate = 0
            
            # 分母：投入资本
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
            
            net_income = profit_row.get('Net income') or profit_row.get('净利润') or 0
            total_revenue = (
                profit_row.get('Total revenue') or 
                profit_row.get('营业收入') or 
                profit_row.get('主营收入') or 0
            )
            
            results.append({
                'year': year,
                'roic': round(roic, 2),
                'nopat': round(nopat / 100000000, 2),
                'invested_capital': round(invested_capital / 100000000, 2),
                'operate_profit': round(operating_income / 100000000, 2),
                'tax_rate': round(tax_rate, 4),
                'net_profit': round(net_income / 100000000, 2),
                'revenue': round(total_revenue / 100000000, 2)
            })
        except IndexError:
            continue
            
    return pd.DataFrame(results).sort_values('year')


def calculate_roic(market: str, code: str, years: int = 5) -> pd.DataFrame:
    """
    统一的 ROIC 计算入口
    
    Args:
        market: 'A股', '港股', '美股'
        code: 股票代码
        years: 年数
    
    Returns:
        DataFrame
    """
    if market == 'A股':
        return calculate_roic_a_share(code, years)
    elif market == '港股':
        return calculate_roic_hk(code, years)
    elif market == '美股':
        return calculate_roic_us(code, years)

    raise ValueError(f"不支持的市场类型：{market}，请选择 'A股'、'港股' 或 '美股'")
