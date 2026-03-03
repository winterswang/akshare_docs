#!/usr/bin/env python3
"""
AkShare API 可用性测试 - 修复版
修复：
1. JSON 序列化（date 对象处理）
2. 状态文件读写
3. 错误处理
"""

import os
import sys
import json
import time
import random
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import akshare as ak
except ImportError:
    print("请先安装 akshare: pip install akshare")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    api_name: str
    category: str
    status: str
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


CATEGORY_RULES = {
    'stock': ['stock_', 'equity', 'a_stock', 'zh_a', 'bj_a', 'sh_a', 'sz_a'],
    'fund': ['fund_', 'etf', 'fund'],
    'bond': ['bond_'],
    'futures': ['futures_', 'fut_', 'option_'],
    'forex': ['fx_', 'forex', 'currency_'],
    'crypto': ['crypto_', 'btc', 'eth', 'bitcoin'],
    'macro': ['macro_', 'economy_'],
    'news': ['news_', 'notice_'],
    'other': []
}


def classify_api(api_name: str) -> str:
    api_lower = api_name.lower()
    for category, keywords in CATEGORY_RULES.items():
        if category == 'other':
            continue
        for keyword in keywords:
            if keyword in api_lower:
                return category
    return 'other'


def test_single_api(api_name: str, timeout: int = 30) -> TestResult:
    category = classify_api(api_name)
    
    try:
        if not hasattr(ak, api_name):
            return TestResult(
                api_name=api_name,
                category=category,
                status='error',
                error=f"API not found",
                error_type='not_found'
            )
        
        func = getattr(ak, api_name)
        start_time = time.time()
        
        try:
            # 尝试无参数调用
            df = func()
            end_time = time.time()
            return TestResult(
                api_name=api_name,
                category=category,
                status='success',
                response_time_ms=int((end_time - start_time) * 1000)
            )
        except TypeError:
            # 需要参数
            try:
                df = func(symbol='000001')
                end_time = time.time()
                return TestResult(
                    api_name=api_name,
                    category=category,
                    status='success',
                    response_time_ms=int((end_time - start_time) * 1000)
                )
            except Exception as e:
                return TestResult(
                    api_name=api_name,
                    category=category,
                    status='failed',
                    error=str(e)[:100],
                    error_type=type(e).__name__
                )
        except Exception as e:
            error_str = str(e)[:100]
            return TestResult(
                api_name=api_name,
                category=category,
                status='failed',
                error=error_str,
                error_type=type(e).__name__
            )
    except Exception as e:
        return TestResult(
            api_name=api_name,
            category=category,
            status='error',
            error=str(e)[:100],
            error_type=type(e).__name__
        )


def load_apis(skills_path: str) -> List[str]:
    with open(skills_path, 'r', encoding='utf-8') as f:
        skills = json.load(f)
    return [s['function']['name'] for s in skills if s.get('type') == 'function']


def main():
    parser = argparse.ArgumentParser(description='AkShare API 测试')
    parser.add_argument('--start', type=int, default=0, help='起始索引')
    parser.add_argument('--end', type=int, default=-1, help='结束索引 (-1 表示全部)')
    parser.add_argument('--delay-min', type=float, default=2, help='最小延迟(秒)')
    parser.add_argument('--delay-max', type=float, default=5, help='最大延迟(秒)')
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    skills_path = project_root / 'docs' / 'skills.json'
    output_dir = project_root / 'reports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载 API 列表
    apis = load_apis(str(skills_path))
    total = len(apis)
    
    # 确定范围
    start = args.start
    end = args.end if args.end > 0 else total
    
    logger.info(f"共 {total} 个 API")
    logger.info(f"测试范围: {start+1} - {end}")
    
    results = {}
    test_start = time.time()
    
    for i in range(start, end):
        api_name = apis[i]
        logger.info(f"[{i+1}/{total}] 测试: {api_name}")
        
        result = test_single_api(api_name)
        results[api_name] = asdict(result)
        
        emoji = {'success': '✅', 'failed': '❌', 'error': '⚠️'}.get(result.status, '❓')
        logger.info(f"  {emoji} {result.status} ({result.response_time_ms or '-'}ms)")
        
        # 每 10 个保存一次
        if (i + 1) % 10 == 0 or i == end - 1:
            success = sum(1 for r in results.values() if r['status'] == 'success')
            failed = sum(1 for r in results.values() if r['status'] == 'failed')
            error = sum(1 for r in results.values() if r['status'] == 'error')
            
            report = {
                'test_date': datetime.now().strftime('%Y-%m-%d'),
                'test_time': datetime.now().strftime('%H:%M:%S'),
                'progress': {'current': i + 1, 'total': total},
                'summary': {'success': success, 'failed': failed, 'error': error},
                'apis': results
            }
            
            temp_path = output_dir / '.progress.json'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        # 延迟
        if i < end - 1:
            time.sleep(random.uniform(args.delay_min, args.delay_max))
    
    test_end = time.time()
    
    # 最终报告
    success = sum(1 for r in results.values() if r['status'] == 'success')
    failed = sum(1 for r in results.values() if r['status'] == 'failed')
    error = sum(1 for r in results.values() if r['status'] == 'error')
    
    # 按分类统计
    by_category = {}
    for api_name, result in results.items():
        cat = result['category']
        if cat not in by_category:
            by_category[cat] = {'total': 0, 'success': 0, 'failed': 0, 'error': 0}
        by_category[cat]['total'] += 1
        by_category[cat][result['status']] += 1
    
    final_report = {
        'test_date': datetime.now().strftime('%Y-%m-%d'),
        'test_time': datetime.now().strftime('%H:%M:%S'),
        'duration_seconds': int(test_end - test_start),
        'summary': {
            'total': len(results),
            'success': success,
            'failed': failed,
            'error': error,
            'by_category': by_category
        },
        'apis': results
    }
    
    report_path = output_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2, default=str)
    
    # 清理临时文件
    (output_dir / '.progress.json').unlink(missing_ok=True)
    
    print("\n" + "="*60)
    print("📊 测试完成")
    print("="*60)
    print(f"测试数: {len(results)}")
    print(f"成功: {success} ({success/len(results)*100:.1f}%)")
    print(f"失败: {failed}")
    print(f"错误: {error}")
    print(f"耗时: {int(test_end - test_start)} 秒")
    print(f"报告: {report_path}")
    print("="*60)


if __name__ == '__main__':
    main()