# AkShare 标准化数据接口使用指南

## 快速开始

### 1. 基本使用

```python
import sys
sys.path.insert(0, '/root/.openclaw/workspace/akshare_docs')

from akshare_service.skills import (
    get_financial_summary,
    get_cashflow_data,
    get_valuation_data
)

# 获取财务指标
financial = get_financial_summary("300760", years=5)

# 获取现金流数据
cashflow = get_cashflow_data("300760", years=5)

# 获取估值数据
valuation = get_valuation_data("300760")
```

### 2. 数据源路由

系统会自动选择最佳数据源：

```
优先级: TuShare → AkShare(新浪) → AkShare(东财)
```

### 3. 配置 TuShare（推荐）

**步骤：**

1. 注册 TuShare：https://tushare.pro
2. 获取 Token
3. 配置环境变量：

```bash
# 方式一：临时设置
export TUSHARE_TOKEN="your_token_here"

# 方式二：永久设置（添加到 ~/.bashrc）
echo 'export TUSHARE_TOKEN="your_token_here"' >> ~/.bashrc
source ~/.bashrc

# 方式三：在代码中设置
import os
os.environ['TUSHARE_TOKEN'] = 'your_token_here'
```

### 4. 缓存机制

- **缓存目录**：`/tmp/akshare_cache/`
- **默认过期**：1 小时
- **自动清理**：过期缓存自动删除

```python
# 使用缓存（默认）
result = get_financial_summary("300760", use_cache=True, cache_ttl=3600)

# 不使用缓存
result = get_financial_summary("300760", use_cache=False)
```

---

## 输出格式

### 财务指标

```json
{
  "code": "300760",
  "source": "TuShare.fina_indicator",
  "annual_data": [
    {
      "year": 2024,
      "revenue": {"value": 367.26, "unit": "亿元", "yoy_growth": 5.14},
      "net_profit": {"value": 116.68, "unit": "亿元", "yoy_growth": 0.74},
      "gross_margin": {"value": 63.11, "unit": "%"},
      "roe": {"value": 28.63, "unit": "%"},
      "debt_ratio": {"value": 28.04, "unit": "%"}
    }
  ]
}
```

### 现金流数据

```json
{
  "code": "300760",
  "source": "TuShare.cashflow",
  "annual_data": [
    {
      "year": 2024,
      "operating_cashflow": {"value": 124.32, "unit": "亿元"},
      "capital_expenditure": {"value": 19.59, "unit": "亿元"},
      "free_cashflow": {"value": 104.73, "unit": "亿元"},
      "fcf_to_netprofit": {"value": 89.75, "unit": "%"}
    }
  ]
}
```

---

## 文件结构

```
akshare_docs/
├── akshare_service/
│   ├── adapters/                  # 数据源适配器
│   │   ├── __init__.py
│   │   └── tushare_adapter.py     # TuShare 适配器
│   ├── infra/
│   │   └── cache.py               # 缓存模块
│   └── skills/
│       ├── financial_summary.py   # 财务指标（多源路由）
│       ├── cashflow.py            # 现金流（多源路由）
│       ├── valuation.py           # 估值数据
│       ├── finance.py             # ROIC 计算
│       └── market.py              # 行情数据
└── docs/
    └── api_research.md            # API 调研报告
```

---

## 常见问题

### Q: 为什么返回空数据？

可能原因：
1. API 限速 - 等待几分钟后重试
2. TuShare Token 未配置 - 配置环境变量
3. 股票代码错误 - 检查代码格式

### Q: 如何获取 TuShare Token？

1. 访问 https://tushare.pro
2. 注册账号
3. 在"个人中心"获取 Token

### Q: 数据源如何选择？

系统自动选择：
1. 优先 TuShare（需配置 Token）
2. 其次 AkShare 新浪
3. 最后 AkShare 东财

---

*更新时间: 2026-03-10*