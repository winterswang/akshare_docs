#!/usr/bin/env python3
"""
AkShare API 可用性测试脚本 - 支持分批测试
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
from typing import Dict, List, Optional
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
    sample_keys: Optional[List[str]] = None
    sample_dtypes: Optional[Dict[str, str]] = None
    sample_data: Optional[List[Dict]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None


CATEGORY_RULES = {
    'stock': ['stock_', 'equity', 'a_stock', 'zh_a', 'bj_a', 'sh_a', 'sz_a'],
    'fund': ['fund_', 'etf', 'fund'],
    'bond': ['bond_', 'bond'],
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


def get_sample_params(api_name: str, parameters: Dict) -> Dict:
    sample_params = {}
    props = parameters.get('properties', {})
    for param_name, param_info in props.items():
        if param_name in ['symbol', 'code', 'ts_code']:
            sample_params[param_name] = '000001'
        elif param_name in ['start_date', 'begin']:
            sample_params[param_name] = '20240101'
        elif param_name in ['end_date', 'end']:
            sample_params[param_name] = '20240131'
        elif param_name in ['period']:
            sample_params[param_name] = 'daily'
        elif param_name in ['adjust']:
            sample_params[param_name] = ''
    return sample_params


def test_single_api(api_name: str, parameters: Dict, timeout: int = 30) -> TestResult:
    category = classify_api(api_name)
    
    try:
        if not hasattr(ak, api_name):
            return TestResult(
                api_name=api_name,
                category=category,
                status='error',
                error=f"API '{api_name}' 不存在",
                error_type='not_found'
            )
        
        func = getattr(ak, api_name)
        sample_params = get_sample_params(api_name, parameters)
        
        start_time = time.time()
        
        try:
            if sample_params:
                df = func(**sample_params)
            else:
                df = func()
            
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            if df is None:
                return TestResult(
                    api_name=api_name,
                    category=category,
                    status='success',
                    response_time_ms=response_time_ms,
                    sample_keys=[],
                    sample_data=[]
                )
            
            if hasattr(df, 'to_dict'):
                sample_data = df.head(3).to_dict('records') if len(df) > 0 else []
                sample_keys = list(df.columns) if hasattr(df, 'columns') else []
                sample_dtypes = {col: str(df[col].dtype) for col in df.columns} if hasattr(df, 'columns') else {}
            elif isinstance(df, dict):
                sample_data = [df] if df else []
                sample_keys = list(df.keys()) if df else []
                sample_dtypes = {k: type(v).__name__ for k, v in df.items()} if df else {}
            elif isinstance(df, list):
                sample_data = df[:3] if df else []
                sample_keys = list(df[0].keys()) if df and isinstance(df[0], dict) else []
                sample_dtypes = {}
            else:
                sample_data = []
                sample_keys = []
                sample_dtypes = {}
            
            return TestResult(
                api_name=api_name,
                category=category,
                status='success',
                response_time_ms=response_time_ms,
                sample_keys=sample_keys,
                sample_dtypes=sample_dtypes,
                sample_data=sample_data[:3]
            )
            
        except Exception as e:
            return TestResult(
                api_name=api_name,
                category=category,
                status='failed',
                error=str(e)[:200],
                error_type=type(e).__name__
            )
            
    except Exception as e:
        return TestResult(
            api_name=api_name,
            category=category,
            status='error',
            error=str(e)[:200],
            error_type=type(e).__name__
        )


def load_apis_from_skills(skills_path: str) -> List[Dict]:
    with open(skills_path, 'r', encoding='utf-8') as f:
        skills = json.load(f)
    
    apis = []
    for skill in skills:
        if skill.get('type') == 'function':
            func = skill.get('function', {})
            apis.append({
                'name': func.get('name', ''),
                'description': func.get('description', ''),
                'parameters': func.get('parameters', {})
            })
    return apis


def load_state(state_path: str) -> Dict:
    """加载测试状态"""
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'total_apis': 0,
        'tested_count': 0,
        'current_batch': 0,
        'batch_size': 50,
        'results': {},
        'summary': {'total': 0, 'success': 0, 'failed': 0, 'timeout': 0, 'error': 0}
    }


def save_state(state_path: str, state: Dict):
    """保存测试状态"""
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description='AkShare API 可用性测试 - 分批模式')
    parser.add_argument('--skills', default='docs/skills.json', help='skills.json 路径')
    parser.add_argument('--output', default='reports', help='输出目录')
    parser.add_argument('--delay-min', type=float, default=2, help='最小请求间隔(秒)')
    parser.add_argument('--delay-max', type=float, default=5, help='最大请求间隔(秒)')
    parser.add_argument('--timeout', type=int, default=30, help='API 超时时间(秒)')
    parser.add_argument('--batch', type=int, default=50, help='每批测试数量')
    parser.add_argument('--batch-index', type=int, default=None, help='指定批次索引（从0开始）')
    parser.add_argument('--reset', action='store_true', help='重置测试状态')
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    skills_path = project_root / args.skills
    output_dir = project_root / args.output
    state_path = output_dir / 'test_state.json'
    
    if not skills_path.exists():
        logger.error(f"skills.json 不存在: {skills_path}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 加载 API 列表
    logger.info(f"加载 API 列表: {skills_path}")
    apis = load_apis_from_skills(str(skills_path))
    total_apis = len(apis)
    logger.info(f"共 {total_apis} 个 API")
    
    # 加载或初始化状态
    if args.reset:
        state = load_state('')
        state['total_apis'] = total_apis
        state['batch_size'] = args.batch
        logger.info("已重置测试状态")
    else:
        state = load_state(str(state_path))
        if state['total_apis'] == 0:
            state['total_apis'] = total_apis
            state['batch_size'] = args.batch
    
    # 计算批次
    total_batches = (total_apis + args.batch - 1) // args.batch
    
    # 确定当前批次
    if args.batch_index is not None:
        batch_index = args.batch_index
    else:
        batch_index = state['current_batch']
    
    if batch_index >= total_batches:
        logger.info(f"所有批次已完成！共 {total_batches} 批")
        batch_index = 0  # 从头开始新一轮
    
    start_idx = batch_index * args.batch
    end_idx = min(start_idx + args.batch, total_apis)
    
    logger.info(f"开始批次 {batch_index + 1}/{total_batches} (API {start_idx + 1}-{end_idx})")
    
    # 测试当前批次
    batch_results = {}
    batch_start_time = time.time()
    
    for i in range(start_idx, end_idx):
        api_info = apis[i]
        api_name = api_info['name']
        parameters = api_info.get('parameters', {})
        
        logger.info(f"[{i+1}/{total_apis}] 测试: {api_name}")
        
        result = test_single_api(api_name, parameters, args.timeout)
        batch_results[api_name] = result
        
        status_emoji = {'success': '✅', 'failed': '❌', 'timeout': '⏱️', 'error': '⚠️'}
        emoji = status_emoji.get(result.status, '❓')
        logger.info(f"  {emoji} {result.status} ({result.response_time_ms or '-'}ms)")
        
        # 随机延迟
        if i < end_idx - 1:
            delay = random.uniform(args.delay_min, args.delay_max)
            time.sleep(delay)
    
    batch_end_time = time.time()
    batch_duration = int(batch_end_time - batch_start_time)
    
    # 更新状态
    state['results'].update({name: asdict(r) for name, r in batch_results.items()})
    state['tested_count'] = len(state['results'])
    state['current_batch'] = batch_index + 1
    
    # 计算汇总
    success = sum(1 for r in state['results'].values() if r['status'] == 'success')
    failed = sum(1 for r in state['results'].values() if r['status'] == 'failed')
    timeout = sum(1 for r in state['results'].values() if r['status'] == 'timeout')
    error = sum(1 for r in state['results'].values() if r['status'] == 'error')
    
    state['summary'] = {
        'total': total_apis,
        'tested': state['tested_count'],
        'success': success,
        'failed': failed,
        'timeout': timeout,
        'error': error
    }
    
    # 保存状态
    save_state(str(state_path), state)
    logger.info(f"状态已保存: {state_path}")
    
    # 输出批次汇总
    batch_success = sum(1 for r in batch_results.values() if r.status == 'success')
    batch_failed = sum(1 for r in batch_results.values() if r.status == 'failed')
    batch_timeout = sum(1 for r in batch_results.values() if r.status == 'timeout')
    batch_error = sum(1 for r in batch_results.values() if r.status == 'error')
    
    print("\n" + "="*50)
    print(f"📊 批次 {batch_index + 1}/{total_batches} 完成")
    print("="*50)
    print(f"本批测试: {len(batch_results)} 个 API")
    print(f"成功: {batch_success} ({batch_success/len(batch_results)*100:.1f}%)")
    print(f"失败: {batch_failed}")
    print(f"超时: {batch_timeout}")
    print(f"错误: {batch_error}")
    print(f"耗时: {batch_duration} 秒")
    print("-"*50)
    print(f"总体进度: {state['tested_count']}/{total_apis} ({state['tested_count']/total_apis*100:.1f}%)")
    print(f"总体成功率: {success}/{state['tested_count']} ({success/state['tested_count']*100:.1f}%)")
    print("="*50)
    
    # 如果所有批次完成，生成最终报告
    if state['tested_count'] >= total_apis:
        logger.info("所有 API 测试完成，生成最终报告...")
        
        # 计算分类统计
        by_category = {}
        for api_name, result in state['results'].items():
            cat = result['category']
            if cat not in by_category:
                by_category[cat] = {'total': 0, 'success': 0, 'failed': 0, 'timeout': 0, 'error': 0}
            by_category[cat]['total'] += 1
            by_category[cat][result['status']] += 1
        
        final_report = {
            'test_date': datetime.now().strftime('%Y-%m-%d'),
            'test_time': datetime.now().strftime('%H:%M:%S'),
            'summary': {
                **state['summary'],
                'by_category': by_category
            },
            'apis': state['results']
        }
        
        report_path = output_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
        logger.info(f"最终报告已保存: {report_path}")


if __name__ == '__main__':
    main()