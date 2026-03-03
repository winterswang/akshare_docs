#!/usr/bin/env python3
"""
报告生成器

生成 HTML 可视化报告
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AkShare API 测试报告 - {date}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        /* 头部 */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 24px; margin-bottom: 10px; }
        .header .meta { opacity: 0.9; font-size: 14px; }
        
        /* 统计卡片 */
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .stat-card .value { font-size: 32px; font-weight: bold; margin-bottom: 5px; }
        .stat-card .label { color: #666; font-size: 14px; }
        .stat-card.success .value { color: #10b981; }
        .stat-card.failed .value { color: #ef4444; }
        .stat-card.timeout .value { color: #f59e0b; }
        .stat-card.total .value { color: #3b82f6; }
        
        /* 图表区域 */
        .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        @media (max-width: 768px) { .charts { grid-template-columns: 1fr; } }
        .chart-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .chart-card h3 { margin-bottom: 15px; font-size: 16px; }
        
        /* 变更列表 */
        .changes { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .changes h3 { margin-bottom: 15px; }
        .change-item { padding: 10px; border-bottom: 1px solid #eee; }
        .change-item:last-child { border-bottom: none; }
        .change-item.success { color: #10b981; }
        .change-item.failed { color: #ef4444; }
        .change-item.warning { color: #f59e0b; }
        
        /* 详情表格 */
        .details { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }
        .details h3 { padding: 20px; border-bottom: 1px solid #eee; }
        
        /* 筛选器 */
        .filters { padding: 15px 20px; background: #f9fafb; border-bottom: 1px solid #eee; }
        .filters select, .filters input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; margin-right: 10px; }
        
        /* 表格 */
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f9fafb; font-weight: 600; }
        tr:hover { background: #f9fafb; }
        
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-badge.success { background: #d1fae5; color: #065f46; }
        .status-badge.failed { background: #fee2e2; color: #991b1b; }
        .status-badge.timeout { background: #fef3c7; color: #92400e; }
        .status-badge.error { background: #f3f4f6; color: #374151; }
        
        .category-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            background: #e0e7ff;
            color: #3730a3;
        }
        
        /* 错误信息 */
        .error-msg { 
            max-width: 300px; 
            overflow: hidden; 
            text-overflow: ellipsis; 
            white-space: nowrap;
            font-size: 12px;
            color: #666;
        }
        
        /* 无变更提示 */
        .no-changes { text-align: center; padding: 30px; color: #10b981; }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>📊 AkShare API 测试报告</h1>
            <div class="meta">
                测试日期: {date} {time} | 耗时: {duration} 秒
            </div>
        </div>
        
        <!-- 统计卡片 -->
        <div class="stats">
            <div class="stat-card total">
                <div class="value">{total}</div>
                <div class="label">总接口数</div>
            </div>
            <div class="stat-card success">
                <div class="value">{success}</div>
                <div class="label">成功 ({success_rate}%)</div>
            </div>
            <div class="stat-card failed">
                <div class="value">{failed}</div>
                <div class="label">失败</div>
            </div>
            <div class="stat-card timeout">
                <div class="value">{timeout}</div>
                <div class="label">超时</div>
            </div>
        </div>
        
        <!-- 图表 -->
        <div class="charts">
            <div class="chart-card">
                <h3>分类统计</h3>
                <canvas id="categoryChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>状态分布</h3>
                <canvas id="statusChart"></canvas>
            </div>
        </div>
        
        <!-- 变更情况 -->
        <div class="changes">
            <h3>🔄 变更情况</h3>
            {changes_content}
        </div>
        
        <!-- 详情表格 -->
        <div class="details">
            <h3>📋 接口详情</h3>
            <div class="filters">
                <select id="categoryFilter">
                    <option value="">所有分类</option>
                    {category_options}
                </select>
                <select id="statusFilter">
                    <option value="">所有状态</option>
                    <option value="success">成功</option>
                    <option value="failed">失败</option>
                    <option value="timeout">超时</option>
                    <option value="error">错误</option>
                </select>
                <input type="text" id="searchInput" placeholder="搜索接口名称...">
            </div>
            <table>
                <thead>
                    <tr>
                        <th>接口名称</th>
                        <th>分类</th>
                        <th>状态</th>
                        <th>响应时间</th>
                        <th>返回字段</th>
                        <th>错误信息</th>
                    </tr>
                </thead>
                <tbody id="apiTable">
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // 分类统计图
        const categoryCtx = document.getElementById('categoryChart').getContext('2d');
        new Chart(categoryCtx, {{
            type: 'bar',
            data: {{
                labels: {category_labels},
                datasets: [{{
                    label: '成功数',
                    data: {category_success},
                    backgroundColor: '#10b981'
                }}, {{
                    label: '失败数',
                    data: {category_failed},
                    backgroundColor: '#ef4444'
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{ x: {{ stacked: true }}, y: {{ stacked: true }} }}
            }}
        }});
        
        // 状态分布图
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        new Chart(statusCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['成功', '失败', '超时', '错误'],
                datasets: [{{
                    data: [{success}, {failed}, {timeout}, {error}],
                    backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#6b7280']
                }}]
            }},
            options: {{ responsive: true }}
        }});
        
        // 筛选功能
        document.getElementById('categoryFilter').addEventListener('change', filterTable);
        document.getElementById('statusFilter').addEventListener('change', filterTable);
        document.getElementById('searchInput').addEventListener('input', filterTable);
        
        function filterTable() {{
            const category = document.getElementById('categoryFilter').value;
            const status = document.getElementById('statusFilter').value;
            const search = document.getElementById('searchInput').value.toLowerCase();
            
            document.querySelectorAll('#apiTable tr').forEach(row => {{
                const rowCategory = row.dataset.category;
                const rowStatus = row.dataset.status;
                const rowName = row.dataset.name;
                
                const matchCategory = !category || rowCategory === category;
                const matchStatus = !status || rowStatus === status;
                const matchSearch = !search || rowName.includes(search);
                
                row.style.display = matchCategory && matchStatus && matchSearch ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>
'''


def generate_html_report(report_data: Dict, output_path: str):
    """生成 HTML 报告"""
    
    summary = report_data.get('summary', {})
    changes = report_data.get('changes', {})
    apis = report_data.get('apis', {})
    
    # 基础统计
    total = summary.get('total', 0)
    success = summary.get('success', 0)
    failed = summary.get('failed', 0)
    timeout = summary.get('timeout', 0)
    error = summary.get('error', 0)
    success_rate = round(success / total * 100, 1) if total > 0 else 0
    
    # 分类数据
    by_category = summary.get('by_category', {})
    categories = sorted(by_category.keys())
    category_labels = json.dumps(categories)
    category_success = json.dumps([by_category.get(c, {}).get('success', 0) for c in categories])
    category_failed = json.dumps([by_category.get(c, {}).get('failed', 0) + by_category.get(c, {}).get('timeout', 0) for c in categories])
    
    # 分类选项
    category_options = '\n'.join([f'<option value="{c}">{c}</option>' for c in categories])
    
    # 变更内容
    changes_content = generate_changes_html(changes)
    
    # 表格行
    table_rows = []
    for api_name, api_info in sorted(apis.items()):
        status_class = api_info.get('status', 'error')
        status_text = {
            'success': '成功',
            'failed': '失败', 
            'timeout': '超时',
            'error': '错误'
        }.get(status_class, status_class)
        
        category = api_info.get('category', 'other')
        response_time = api_info.get('response_time_ms', '-')
        sample_keys = api_info.get('sample_keys', [])
        error_msg = api_info.get('error', '') or ''
        
        row = f'''<tr data-category="{category}" data-status="{status_class}" data-name="{api_name}">
            <td><code>{api_name}</code></td>
            <td><span class="category-badge">{category}</span></td>
            <td><span class="status-badge {status_class}">{status_text}</span></td>
            <td>{response_time}ms</td>
            <td>{len(sample_keys)} 个字段</td>
            <td class="error-msg" title="{error_msg}">{error_msg[:50]}</td>
        </tr>'''
        table_rows.append(row)
    
    # 填充模板
    html = HTML_TEMPLATE.format(
        date=report_data.get('test_date', '-'),
        time=report_data.get('test_time', '-'),
        duration=report_data.get('duration_seconds', '-'),
        total=total,
        success=success,
        failed=failed,
        timeout=timeout,
        error=error,
        success_rate=success_rate,
        category_labels=category_labels,
        category_success=category_success,
        category_failed=category_failed,
        category_options=category_options,
        changes_content=changes_content,
        table_rows='\n'.join(table_rows)
    )
    
    # 写入文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


def generate_changes_html(changes: Dict) -> str:
    """生成变更部分的 HTML"""
    lines = []
    
    # 新增接口
    if changes.get('new_apis'):
        lines.append('<div class="change-item success">')
        lines.append(f'<strong>✨ 新增接口 ({len(changes["new_apis"])} 个):</strong>')
        for api in changes['new_apis'][:5]:
            lines.append(f'<br>+ {api}')
        if len(changes['new_apis']) > 5:
            lines.append(f'<br>... 还有 {len(changes["new_apis"]) - 5} 个')
        lines.append('</div>')
    
    # 移除接口
    if changes.get('removed_apis'):
        lines.append('<div class="change-item failed">')
        lines.append(f'<strong>🗑️ 移除接口 ({len(changes["removed_apis"])} 个):</strong>')
        for api in changes['removed_apis'][:5]:
            lines.append(f'<br>- {api}')
        lines.append('</div>')
    
    # 状态变更
    if changes.get('status_changed'):
        lines.append('<div class="change-item warning">')
        lines.append(f'<strong>🔄 状态变更 ({len(changes["status_changed"])} 个):</strong>')
        for item in changes['status_changed'][:5]:
            lines.append(f'<br>{item["api"]}: {item["from"]} → {item["to"]}')
        lines.append('</div>')
    
    # 结构变更
    if changes.get('structure_changed'):
        lines.append('<div class="change-item">')
        lines.append(f'<strong>📐 结构变更 ({len(changes["structure_changed"])} 个):</strong>')
        for item in changes['structure_changed'][:3]:
            if item.get('added_fields'):
                lines.append(f'<br>{item["api"]}: 新增字段 {item["added_fields"]}')
        lines.append('</div>')
    
    if not lines:
        return '<div class="no-changes">✅ 今日无变更</div>'
    
    return '\n'.join(lines)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='生成 HTML 报告')
    parser.add_argument('report', help='JSON 报告路径')
    parser.add_argument('--output', '-o', help='输出路径 (默认: 同目录同名 .html)')
    
    args = parser.parse_args()
    
    with open(args.report, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    if args.output:
        output_path = args.output
    else:
        output_path = args.report.replace('.json', '.html')
    
    generate_html_report(report_data, output_path)
    print(f"HTML 报告已生成: {output_path}")