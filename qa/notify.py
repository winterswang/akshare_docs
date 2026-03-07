#!/usr/bin/env python3
"""
飞书推送模块

发送测试报告摘要到飞书
"""

import sys
import os
import requests
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, Optional

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from qa import comparator
except ImportError:
    import comparator


def format_summary(report: Dict) -> str:
    """格式化摘要信息"""
    summary = report.get('summary', {})
    changes = report.get('changes', {})
    
    total = summary.get('total', 0)
    success = summary.get('success', 0)
    failed = summary.get('failed', 0)
    timeout = summary.get('timeout', 0)
    error = summary.get('error', 0)
    
    success_rate = round(success / total * 100, 1) if total > 0 else 0
    
    lines = []
    lines.append(f"📊 **akshare 每日检测报告 - {report.get('test_date', '未知')}**")
    lines.append("")
    lines.append(f"✅ **成功率：{success_rate}%** ({success}/{total})")
    lines.append(f"❌ 失败：{failed} | ⏱️ 超时：{timeout} | ⚠️ 错误：{error}")
    lines.append(f"⏱️ 耗时：{report.get('duration_seconds', '-')} 秒")
    lines.append("")
    
    # 变更情况
    if changes:
        new_apis = changes.get('new_apis', [])
        removed_apis = changes.get('removed_apis', [])
        status_changed = changes.get('status_changed', [])
        structure_changed = changes.get('structure_changed', [])
        
        if new_apis or removed_apis or status_changed or structure_changed:
            lines.append("🔄 **变更情况：**")
            
            if new_apis:
                lines.append(f"• 新增接口：{len(new_apis)} 个")
                for api in new_apis[:3]:
                    lines.append(f"  - {api}")
                if len(new_apis) > 3:
                    lines.append(f"  - ... 还有 {len(new_apis) - 3} 个")
            
            if removed_apis:
                lines.append(f"• 移除接口：{len(removed_apis)} 个")
            
            if status_changed:
                lines.append(f"• 状态变更：{len(status_changed)} 个")
                for item in status_changed[:3]:
                    from_status = {'success': '✅', 'failed': '❌', 'timeout': '⏱️'}.get(item['from'], '❓')
                    to_status = {'success': '✅', 'failed': '❌', 'timeout': '⏱️'}.get(item['to'], '❓')
                    lines.append(f"  - {item['api']}: {from_status} → {to_status}")
            
            if structure_changed:
                lines.append(f"• 结构变更：{len(structure_changed)} 个")
            
            lines.append("")
    
    # 分类统计
    by_category = summary.get('by_category', {})
    if by_category:
        lines.append("📋 **分类统计：**")
        for cat, stats in sorted(by_category.items()):
            cat_success = stats.get('success', 0)
            cat_total = stats.get('total', 0)
            cat_rate = round(cat_success / cat_total * 100) if cat_total > 0 else 0
            lines.append(f"• {cat}：{cat_success}/{cat_total} 成功 ({cat_rate}%)")
    
    return "\n".join(lines)


def send_to_feishu(webhook_url: str, message: str) -> bool:
    """
    发送消息到飞书
    
    Args:
        webhook_url: 飞书机器人 Webhook URL
        message: 消息内容
        
    Returns:
        是否发送成功
    """
    if not webhook_url:
        print("未配置飞书 Webhook URL")
        return False
    
    payload = {
        "msg_type": "text",
        "content": {
            "text": message
        }
    }
    
    # 也发送卡片格式
    card_payload = {
        "msg_type": "interactive",
        "card": {
            "elements": [
                {
                    "tag": "markdown",
                    "content": message
                }
            ]
        }
    }
    
    try:
        # 发送文本消息
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                print("飞书推送成功")
                return True
            else:
                print(f"飞书推送失败: {result}")
                return False
    except Exception as e:
        print(f"飞书推送错误: {e}")
        return False


def notify_report(report_path: str, webhook_url: str) -> bool:
    """
    读取报告并发送通知
    
    Args:
        report_path: 报告文件路径
        webhook_url: 飞书 Webhook URL
        
    Returns:
        是否发送成功
    """
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        message = format_summary(report)
        return send_to_feishu(webhook_url, message)
        
    except Exception as e:
        print(f"读取报告失败: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='发送报告到飞书')
    parser.add_argument('report', help='报告文件路径')
    parser.add_argument('--webhook', required=True, help='飞书 Webhook URL')
    
    args = parser.parse_args()
    notify_report(args.report, args.webhook)
