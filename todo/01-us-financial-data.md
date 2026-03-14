# akshare_service 财务数据接口需求

> 创建时间: 2026-03-14
> 状态: TODO
> 归属: company-deep-analysis 项目

---

## 背景

data-collector 模块需要从 akshare_service 获取标准化的财务数据。
当前 akshare_service 只有 ROIC 计算接口，需要扩展获取完整财务数据的能力。

---

## 接口需求

### 1. get_us_financial_data

获取美股财务数据

```python
def get_us_financial_data(
    ticker: str,
    years: int = 5,
    include_ttm: bool = True
) -> dict:
    """
    获取美股财务数据
    
    Args:
        ticker: 股票代码 (e.g., "PDD", "AAPL", "MSFT")
        years: 需要多少年数据 (默认 5 年)
        include_ttm: 是否包含 TTM（当无最新年报时使用）
    
    Returns:
        {
            "ticker": "PDD",
            "market": "us",
            "latest_type": "annual",  # or "ttm" (当无2024年报时)
            "data": [
                {
                    "year": 2024,
                    "type": "annual",  # "annual" | "ttm" | "quarterly"
                    "report_date": "2024-12-31",
                    "metrics": {
                        # 损益表
                        "revenue": 393836097000.0,      # 营业收入 (元)
                        "operating_cost": 153900374000.0,  # 营业成本
                        "gross_profit": 239935723000.0,    # 毛利
                        "rd_expense": ...,                  # 研发费用
                        "marketing_expense": ...,          # 营销费用
                        "admin_expense": ...,              # 管理费用
                        "operating_profit": 108422862000.0, # 营业利润
                        "pretax_income": 132701293000.0,    # 税前利润
                        "income_tax": 20266781000.0,       # 所得税
                        "net_income": 112434512000.0,      # 净利润
                        "eps": 20.31,                       # 每股收益
                    },
                    "derived": {
                        "gross_margin": 60.92,    # 毛利率 %
                        "net_margin": 28.55,     # 净利率 %
                        "operating_margin": 27.53 # 营业利润率 %
                    },
                    "source": "AkShare",
                    "reliability": "P0"
                },
                {
                    "year": 2023,
                    "type": "annual",
                    ...
                },
                # 如果 include_ttm=True 且无2024年报，会返回 TTM 数据
                # {
                #     "year": 2025,
                #     "type": "ttm",
                #     ...
                # }
            ]
        }
    
    Raises:
        ValueError: ticker 无效或市场不支持
        RuntimeError: 数据获取失败
    """
```

---

## 数据字段定义

### 1. 损益表 (Income Statement)

| 字段 | 中文名 | 类型 | 说明 |
|------|--------|------|------|
| `revenue` | 营业收入 | float | 单位：元 |
| `operating_cost` | 营业成本 | float | |
| `gross_profit` | 毛利 | float | revenue - operating_cost |
| `rd_expense` | 研发费用 | float | |
| `marketing_expense` | 营销费用 | float | |
| `admin_expense` | 管理费用 | float | |
| `operating_profit` | 营业利润 | float | |
| `pretax_income` | 税前利润 | float | |
| `income_tax` | 所得税 | float | |
| `net_income` | 净利润 | float | |
| `eps` | 每股收益 | float | 基本每股收益 |

### 2. 衍生指标 (Derived Metrics)

| 字段 | 中文名 | 计算公式 |
|------|--------|----------|
| `gross_margin` | 毛利率 (%) | gross_profit / revenue * 100 |
| `net_margin` | 净利率 (%) | net_income / revenue * 100 |
| `operating_margin` | 营业利润率 (%) | operating_profit / revenue * 100 |

---

## 数据类型规则

### 获取优先级

| 优先级 | 类型 | 说明 |
|--------|------|------|
| 1 | 年度报告 | 最新完整财年 (2024) |
| 2 | TTM | 最近12个月（无2024年报时） |
| 3 | 季度累计 | 部分季度数据 |

### TTM 计算逻辑

```
如果:
  - 有最新年报 → 使用年度报告
  - 无年报但有4个季度 → 4个季度累加 = TTM
  - 只有部分季度 → 可用的季度累加
```

---

## 返回数据可靠性

| 数据源 | 可靠性 | 评级 |
|--------|--------|------|
| AkShare 年报 | 高 | P0 |
| AkShare 季报 | 中 | P1 |
| AkShare TTM | 中-高 | P1 |

---

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| ticker 无效 | 抛出 ValueError |
| 无数据 | 返回空 data 数组，包含 error 字段 |
| 网络错误 | 抛出 RuntimeError，包含原始错误 |

---

## 示例输出

```json
{
  "ticker": "PDD",
  "market": "us",
  "latest_type": "annual",
  "data": [
    {
      "year": 2024,
      "type": "annual",
      "report_date": "2024-12-31",
      "metrics": {
        "revenue": 393836097000.0,
        "operating_cost": 153900374000.0,
        "gross_profit": 239935723000.0,
        "operating_profit": 108422862000.0,
        "pretax_income": 132701293000.0,
        "income_tax": 20266781000.0,
        "net_income": 112434512000.0,
        "eps": 20.31
      },
      "derived": {
        "gross_margin": 60.92,
        "net_margin": 28.55,
        "operating_margin": 27.53
      },
      "source": "AkShare",
      "reliability": "P0"
    },
    ...
  ]
}
```

---

## TODO

- [ ] 实现 `get_us_financial_data` 接口
- [ ] 实现 TTM 数据获取逻辑
- [ ] 添加单元测试
- [ ] 与 data-collector 集成测试

---

*状态: TODO | 创建: 2026-03-14*