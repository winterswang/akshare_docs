#!/bin/bash
# AkShare API 完整测试脚本 - 自动运行所有批次

cd /root/.openclaw/workspace/akshare_docs

echo "=========================================="
echo "AkShare API 可用性测试"
echo "=========================================="
echo "开始时间: $(date)"
echo ""

# 总批次数
TOTAL_BATCHES=8
BATCH_SIZE=50

# 运行所有批次
for batch in $(seq 0 $((TOTAL_BATCHES - 1))); do
    batch_num=$((batch + 1))
    echo ""
    echo "=========================================="
    echo "批次 $batch_num/$TOTAL_BATCHES"
    echo "=========================================="
    
    # 运行当前批次
    python3 scripts/test_apis.py --batch $BATCH_SIZE --batch-index $batch --reset
    
    # 检查是否成功
    if [ $? -eq 0 ]; then
        echo "✅ 批次 $batch_num 完成"
    else
        echo "❌ 批次 $batch_num 失败"
    fi
    
    # 批次间休息
    if [ $batch -lt $((TOTAL_BATCHES - 1)) ]; then
        echo "等待 10 秒后继续下一批..."
        sleep 10
    fi
done

echo ""
echo "=========================================="
echo "所有批次完成"
echo "=========================================="
echo "结束时间: $(date)"

# 显示最终汇总
if [ -f reports/test_state.json ]; then
    echo ""
    echo "=== 最终结果 ==="
    python3 -c "
import json
with open('reports/test_state.json') as f:
    s = json.load(f)
print(f'测试总数: {s[\"tested_count\"]}')
print(f'成功: {s[\"summary\"][\"success\"]}')
print(f'失败: {s[\"summary\"][\"failed\"]}')
print(f'错误: {s[\"summary\"][\"error\"]}')
"
fi