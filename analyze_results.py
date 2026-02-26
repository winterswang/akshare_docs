import json
import statistics
from collections import Counter, defaultdict
import re

RESULTS_FILE = '/Users/wangguangchao/code/langchain_financial/akshare_docs/api_test_results.json'

def analyze():
    with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    stats = Counter(d['status'] for d in data.values())
    
    print(f"=== 测试概览 ===")
    print(f"总接口数: {total}")
    print(f"成功: {stats['success']} ({stats['success']/total*100:.1f}%)")
    print(f"失败 (达到最大重试): {stats['failed_max_retries']} ({stats['failed_max_retries']/total*100:.1f}%)")
    print(f"跳过 (无示例): {stats['skipped_no_example']}")
    print(f"其他状态: {sum(stats.values()) - stats['success'] - stats['failed_max_retries'] - stats['skipped_no_example']}")
    print("\n")

    # Analyze Success Duration
    success_durations = [d['duration'] for d in data.values() if d['status'] == 'success']
    if success_durations:
        print(f"=== 成功接口耗时统计 ===")
        print(f"平均耗时: {statistics.mean(success_durations):.2f}s")
        print(f"中位数耗时: {statistics.median(success_durations):.2f}s")
        print(f"最大耗时: {max(success_durations):.2f}s")
        print(f"最小耗时: {min(success_durations):.2f}s")
        print("\n")

    # Analyze Failures
    print(f"=== 失败原因分析 ===")
    error_counts = defaultdict(list)
    
    for name, res in data.items():
        if res['status'] == 'failed_max_retries':
            error = res.get('error', 'Unknown Error')
            # Simplify error messages for grouping
            if "ProxyError" in error:
                simple_error = "ProxyError (Network/Connection Issue)"
            elif "timeout" in error.lower() or "timed out" in error.lower():
                simple_error = "Timeout"
            elif "404" in error:
                simple_error = "404 Not Found"
            elif "403" in error:
                simple_error = "403 Forbidden"
            elif "KeyError" in error:
                simple_error = "KeyError (Data Parsing Issue)"
            elif "AttributeError" in error:
                simple_error = "AttributeError (Code Compatibility)"
            elif "TypeError" in error:
                simple_error = "TypeError"
            elif "ValueError" in error:
                simple_error = "ValueError"
            elif "IndexError" in error:
                simple_error = "IndexError"
            elif "Expecting value" in error:
                simple_error = "JSON Decode Error"
            elif "'NoneType' object" in error:
                 simple_error = "NoneType Error (Possible missing data)"
            else:
                simple_error = error[:50] + "..." if len(error) > 50 else error
            
            error_counts[simple_error].append(name)

    # Sort by count
    sorted_errors = sorted(error_counts.items(), key=lambda x: len(x[1]), reverse=True)
    
    for error, interfaces in sorted_errors:
        print(f"- {error}: {len(interfaces)} 个接口")
        # Print first 3 examples
        examples = ", ".join(interfaces[:3])
        if len(interfaces) > 3:
            examples += ", ..."
        print(f"  示例: {examples}")

if __name__ == "__main__":
    analyze()
