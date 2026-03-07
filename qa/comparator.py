#!/usr/bin/env python3
"""
结果对比器

对比今日与昨日的测试结果，识别变更
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_report(report_path: str) -> Optional[Dict]:
    """加载报告"""
    if not os.path.exists(report_path):
        return None
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载报告失败: {e}")
        return None


def compare_reports(today: Dict, yesterday: Dict) -> Dict:
    """
    对比两天的报告
    
    Args:
        today: 今日报告
        yesterday: 昨日报告
        
    Returns:
        变更信息
    """
    changes = {
        'new_apis': [],
        'removed_apis': [],
        'status_changed': [],
        'structure_changed': [],
        'performance_changed': []
    }
    
    today_apis = today.get('apis', {})
    yesterday_apis = yesterday.get('apis', {})
    
    today_names = set(today_apis.keys())
    yesterday_names = set(yesterday_apis.keys())
    
    # 新增接口
    new_apis = today_names - yesterday_names
    changes['new_apis'] = sorted(list(new_apis))
    
    # 移除接口
    removed_apis = yesterday_names - today_names
    changes['removed_apis'] = sorted(list(removed_apis))
    
    # 共同接口的变更
    common_apis = today_names & yesterday_names
    
    for api_name in common_apis:
        today_info = today_apis[api_name]
        yesterday_info = yesterday_apis[api_name]
        
        # 状态变更
        today_status = today_info.get('status')
        yesterday_status = yesterday_info.get('status')
        
        if today_status != yesterday_status:
            changes['status_changed'].append({
                'api': api_name,
                'from': yesterday_status,
                'to': today_status
            })
        
        # 结构变更（字段变化）
        if today_status == 'success' and yesterday_status == 'success':
            today_keys = set(today_info.get('sample_keys', []))
            yesterday_keys = set(yesterday_info.get('sample_keys', []))
            
            added_fields = list(today_keys - yesterday_keys)
            removed_fields = list(yesterday_keys - today_keys)
            
            if added_fields or removed_fields:
                changes['structure_changed'].append({
                    'api': api_name,
                    'added_fields': added_fields,
                    'removed_fields': removed_fields
                })
        
        # 性能变更（响应时间变化超过50%）
        today_time = today_info.get('response_time_ms')
        yesterday_time = yesterday_info.get('response_time_ms')
        
        if today_time and yesterday_time and yesterday_time > 0:
            change_ratio = abs(today_time - yesterday_time) / yesterday_time
            if change_ratio > 0.5:  # 变化超过50%
                changes['performance_changed'].append({
                    'api': api_name,
                    'from_ms': yesterday_time,
                    'to_ms': today_time,
                    'change_ratio': round(change_ratio, 2)
                })
    
    return changes


def generate_change_summary(changes: Dict) -> str:
    """生成变更摘要文本"""
    lines = []
    
    # 新增接口
    if changes['new_apis']:
        lines.append(f"✨ 新增接口: {len(changes['new_apis'])} 个")
        for api in changes['new_apis'][:5]:  # 最多显示5个
            lines.append(f"   + {api}")
        if len(changes['new_apis']) > 5:
            lines.append(f"   ... 还有 {len(changes['new_apis']) - 5} 个")
    
    # 移除接口
    if changes['removed_apis']:
        lines.append(f"🗑️ 移除接口: {len(changes['removed_apis'])} 个")
        for api in changes['removed_apis'][:5]:
            lines.append(f"   - {api}")
        if len(changes['removed_apis']) > 5:
            lines.append(f"   ... 还有 {len(changes['removed_apis']) - 5} 个")
    
    # 状态变更
    if changes['status_changed']:
        lines.append(f"🔄 状态变更: {len(changes['status_changed'])} 个")
        for item in changes['status_changed'][:5]:
            from_emoji = {'success': '✅', 'failed': '❌', 'timeout': '⏱️'}.get(item['from'], '❓')
            to_emoji = {'success': '✅', 'failed': '❌', 'timeout': '⏱️'}.get(item['to'], '❓')
            lines.append(f"   {item['api']}: {from_emoji} {item['from']} → {to_emoji} {item['to']}")
        if len(changes['status_changed']) > 5:
            lines.append(f"   ... 还有 {len(changes['status_changed']) - 5} 个")
    
    # 结构变更
    if changes['structure_changed']:
        lines.append(f"📐 结构变更: {len(changes['structure_changed'])} 个")
        for item in changes['structure_changed'][:3]:
            if item['added_fields']:
                lines.append(f"   {item['api']}: 新增字段 {item['added_fields']}")
            if item['removed_fields']:
                lines.append(f"   {item['api']}: 移除字段 {item['removed_fields']}")
    
    # 性能变更
    if changes['performance_changed']:
        lines.append(f"⚡ 性能变更: {len(changes['performance_changed'])} 个")
        for item in changes['performance_changed'][:3]:
            direction = "📈 变慢" if item['to_ms'] > item['from_ms'] else "📉 变快"
            lines.append(f"   {item['api']}: {direction} ({item['from_ms']}ms → {item['to_ms']}ms)")
    
    if not lines:
        lines.append("✅ 无变更")
    
    return '\n'.join(lines)


def get_yesterday_report_path(reports_dir: str, date: Optional[str] = None) -> str:
    """获取昨日报告路径"""
    if date:
        return os.path.join(reports_dir, f"{date}.json")
    
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    return os.path.join(reports_dir, f"{yesterday_str}.json")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='对比测试结果')
    parser.add_argument('today', help='今日报告路径')
    parser.add_argument('yesterday', help='昨日报告路径')
    
    args = parser.parse_args()
    
    today = load_report(args.today)
    yesterday = load_report(args.yesterday)
    
    if not today:
        print(f"无法加载今日报告: {args.today}")
        exit(1)
    
    if not yesterday:
        print(f"无法加载昨日报告: {args.yesterday}")
        exit(1)
    
    changes = compare_reports(today, yesterday)
    print(generate_change_summary(changes))