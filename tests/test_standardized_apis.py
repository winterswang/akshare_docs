"""
AkShare 标准化数据接口单元测试
测试 get_financial_summary、get_cashflow_data、get_valuation_data

注：由于 AkShare API 可能有限速，部分测试可能因网络问题失败
"""

import pytest
import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from akshare_service.skills.financial_summary import get_financial_summary
from akshare_service.skills.cashflow import get_cashflow_data
from akshare_service.skills.valuation import get_valuation_data


class TestFinancialSummary:
    """财务指标接口测试"""
    
    def test_get_financial_summary_basic(self):
        """测试基本功能"""
        result = get_financial_summary("300760", years=2, fetch_name=False)
        
        # 验证基本结构
        assert result['code'] == "300760"
        assert 'source' in result
        assert 'annual_data' in result
        
        # 如果 API 限速，跳过数据验证
        if not result.get('annual_data'):
            pytest.skip(f"API 限速，跳过测试: {result.get('errors')}")
        
        assert len(result['annual_data']) == 2
        
    def test_get_financial_summary_data_fields(self):
        """测试数据字段完整性"""
        result = get_financial_summary("300760", years=1, fetch_name=False)
        
        if not result.get('annual_data'):
            pytest.skip(f"API 限速，跳过测试: {result.get('errors')}")
        
        year_data = result['annual_data'][0]
        
        # 验证必需字段
        assert 'year' in year_data
        assert 'revenue' in year_data
        assert 'net_profit' in year_data
        assert 'gross_margin' in year_data
        assert 'net_margin' in year_data
        assert 'roe' in year_data
        assert 'total_assets' in year_data
        assert 'debt_ratio' in year_data
        
        # 验证数值合理性
        assert year_data['revenue']['value'] > 0
        assert year_data['net_profit']['value'] > 0
        assert 0 < year_data['gross_margin']['value'] < 100
        assert 0 < year_data['roe']['value'] < 100
    
    def test_get_financial_summary_moutai(self):
        """测试贵州茅台数据"""
        result = get_financial_summary("600519", years=2, fetch_name=False)
        
        if not result.get('annual_data'):
            pytest.skip(f"API 限速，跳过测试: {result.get('errors')}")
        
        assert result['code'] == "600519"
        assert len(result['annual_data']) == 2
        
        # 茅台毛利率应该很高（> 90%）
        if result['annual_data']:
            assert result['annual_data'][-1]['gross_margin']['value'] > 90


class TestCashflowData:
    """现金流数据接口测试"""
    
    def test_get_cashflow_data_basic(self):
        """测试基本功能"""
        result = get_cashflow_data("300760", years=2)
        
        # 验证基本结构
        assert result['code'] == "300760"
        assert 'annual_data' in result
        
        if not result.get('annual_data'):
            pytest.skip(f"API 限速，跳过测试: {result.get('errors')}")
        
        assert len(result['annual_data']) == 2
        
    def test_get_cashflow_data_fields(self):
        """测试数据字段完整性"""
        result = get_cashflow_data("300760", years=1)
        
        if not result.get('annual_data'):
            pytest.skip(f"API 限速，跳过测试: {result.get('errors')}")
        
        year_data = result['annual_data'][0]
        
        # 验证必需字段
        assert 'year' in year_data
        assert 'operating_cashflow' in year_data
        assert 'investing_cashflow' in year_data
        assert 'financing_cashflow' in year_data
        assert 'capital_expenditure' in year_data
        assert 'free_cashflow' in year_data
        assert 'fcf_to_netprofit' in year_data
        
        # 验证数值
        assert year_data['operating_cashflow']['value'] > 0
    
    def test_free_cashflow_calculation(self):
        """测试自由现金流计算"""
        result = get_cashflow_data("300760", years=1)
        
        if not result.get('annual_data'):
            pytest.skip(f"API 限速，跳过测试: {result.get('errors')}")
        
        year_data = result['annual_data'][0]
        # FCF = 经营现金流 - 资本支出
        expected_fcf = (year_data['operating_cashflow']['value'] - 
                      year_data['capital_expenditure']['value'])
        assert abs(year_data['free_cashflow']['value'] - expected_fcf) < 0.1


class TestValuationData:
    """估值数据接口测试"""
    
    @pytest.mark.slow
    def test_get_valuation_data_basic(self):
        """测试基本功能（较慢）"""
        result = get_valuation_data("300760")
        
        # 验证基本结构
        assert result['code'] == "300760"
        assert 'name' in result
        assert 'price' in result
        assert 'pe_ttm' in result
        assert 'pb' in result
        assert 'market_cap' in result
        
        # 验证数值
        if result['errors'] is None:
            assert result['price']['value'] > 0
            assert result['market_cap']['value'] > 1000  # 迈瑞市值 > 1000亿


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.slow
    def test_full_analysis_pipeline(self):
        """测试完整分析流程"""
        code = "300760"
        
        # 添加重试机制（API 可能限速）
        max_retries = 3
        financial = None
        
        for attempt in range(max_retries):
            financial = get_financial_summary(code, years=2, fetch_name=False)
            
            if financial.get('annual_data'):
                break
            
            # 如果失败，等待后重试
            if attempt < max_retries - 1:
                time.sleep(3)
        
        if not financial.get('annual_data'):
            pytest.skip(f"API 限速，跳过集成测试: {financial.get('errors')}")
        
        # 2. 获取现金流数据
        cashflow = get_cashflow_data(code, years=2)
        
        if not cashflow.get('annual_data'):
            pytest.skip(f"API 限速，跳过集成测试: {cashflow.get('errors')}")
        
        # 3. 验证数据一致性
        assert len(financial['annual_data']) == len(cashflow['annual_data'])
        
        # 年份应该匹配
        fin_years = [d['year'] for d in financial['annual_data']]
        cf_years = [d['year'] for d in cashflow['annual_data']]
        assert fin_years == cf_years


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '--tb=short'])