# ROIC 计算工具使用说明

**作者：** 小叶  
**创建时间：** 2026-02-24  
**版本：** 1.0

---

## 📌 简介

`roic_calculator.py` 是一个用于计算 A股、港股、美股 ROIC（投入资本回报率）的工具。

### 核心公式

```
投入资本 = 股东权益 + 有息负债 - 现金及等价物
ROIC = NOPAT / 投入资本 × 100%
NOPAT（税后营业利润） = 营业利润 × (1 - 税率)
税率 = 所得税费用 / 利润总额
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install akshare pandas
```

### 2. 运行示例

```bash
cd scripts
python3 roic_calculator.py
```

### 3. 在代码中使用

```python
from roic_calculator import calculate_roic

# A股
df_moutai = calculate_roic('A股', 'SH600519')
print(df_moutai)

# 港股
df_tencent = calculate_roic('港股', '00700')
print(df_tencent)

# 美股
df_pdd = calculate_roic('美股', 'PDD')
print(df_pdd)
```

---

## 📖 API 文档

### calculate_roic(market, code, years=5)

统一的 ROIC 计算入口。

**参数：**

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| market | str | 市场类型：'A股'、'港股'、'美股' | 'A股' |
| code | str | 股票代码 | 'SH600519', '00700', 'PDD' |
| years | int | 年数，默认 5 | 5 |

**返回：**
- `DataFrame`: 包含 ROIC 等数据的数据框

**示例：**

```python
from roic_calculator import calculate_roic

# 获取茅台最近 5 年的 ROIC
df = calculate_roic('A股', 'SH600519', years=5)
print(df)
```

**输出字段：**

| 字段 | 说明 | 单位 |
|------|------|------|
| 年份 | 财务年度 | 年 |
| ROIC | 投入资本回报率 | % |
| NOPAT | 税后营业利润 | 亿元 |
| 投入资本 | 投入资本 | 亿元 |
| 营业利润 | 营业利润 | 亿元 |
| 利润总额 | 利润总额 | 亿元 |
| 所得税费用 | 所得税费用 | 亿元 |
| 税率 | 所得税率 | 小数 |
| 营业总收入 | 营业收入 | 亿元 |
| 净利润 | 净利润 | 亿元 |
| 股东权益 | 股东权益 | 亿元 |
| 有息负债 | 有息负债 | 亿元 |
| 现金及等价物 | 现金 | 亿元 |
| 计算方法 | 计算方法说明 | - |

---

### calculate_roic_a_share(symbol, years=5)

计算 A股 ROIC。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| symbol | str | 股票代码，如 'SH600519' |
| years | int | 年数，默认 5 |

**示例：**

```python
from roic_calculator import calculate_roic_a_share

df = calculate_roic_a_share('SH600519', years=5)
print(df)
```

---

### calculate_roic_hk(stock, years=5)

计算港股 ROIC。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| stock | str | 股票代码，如 '00700' |
| years | int | 年数，默认 5 |

**示例：**

```python
from roic_calculator import calculate_roic_hk

df = calculate_roic_hk('00700', years=5)
print(df)
```

---

### calculate_roic_us(stock, years=5)

计算美股 ROIC。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| stock | str | 股票代码，如 'PDD' |
| years | int | 年数，默认 5 |

**示例：**

```python
from roic_calculator import calculate_roic_us

df = calculate_roic_us('PDD', years=5)
print(df)
```

---

## ⚠️ 重要提示（必须阅读）

### A股（SH600519 茅台）

**错误1：使用错误的营业利润字段**
- ❌ 错误：使用 `OPERATE_INCOME`（值不合理，接近营收）
- ✅ 正确：使用 `OPERATE_PROFIT`（真正的营业利润）

**错误2：使用错误的现金字段**
- ❌ 错误：使用现金流量表的 `END_CASH_EQUIVALENTS`（经常为空）
- ✅ 正确：使用资产负债表的 `MONETARYFUNDS`（货币资金）

**示例（茅台2020年）：**
```
❌ 错误的营业利润（OPERATE_INCOME）：949.15 亿元
✅ 正确的营业利润（OPERATE_PROFIT）：666.35 亿元

❌ 错误的现金（END_CASH_EQUIVALENTS）：0.00 元
✅ 正确的现金（MONETARYFUNDS）：360.91 亿元
```

---

### 港股（00700 腾讯）

**错误：债务字段名称不同**
- ❌ 错误：使用"短期借款"、"长期借款"（字段不存在）
- ✅ 正确：使用"短期贷款"、"长期贷款"（港股对应字段）

**债务字段映射：**

| 标准字段 | 港股字段 | 说明 |
|---------|---------|------|
| 短期借款 | **短期贷款** ✅ | 港股使用"贷款"不是"借款" |
| 长期借款 | **长期贷款** ✅ | 港股使用"贷款"不是"借款" |
| 应付债券 | **应付票据(非流动)** ✅ | 港股对应字段 |

**营业利润字段：**
- ✅ 营业利润：`经营溢利`
- ✅ 利润总额：`除税前溢利`
- ✅ 所得税：`税项`

---

### 美股（PDD）

**错误1：symbol 参数错误**
- ❌ 错误：`symbol="利润表"` 或 `symbol="Income Statement"`
- ✅ 正确：`symbol="综合损益表"`（必须使用中文）

**错误2：数据格式**
- ❌ 错误：直接使用原始数据
- ✅ 正确：必须使用 `pivot()` 进行透视转换

**字段名特点：**
- 美股字段名主要是中文（如"股东权益合计"、"营业利润"）
- 需要支持中英文字段名查询

**示例代码：**

```python
import akshare as ak
import pandas as pd

# 获取利润表（使用"综合损益表"）
df_profit = ak.stock_financial_us_report_em(
    stock="PDD", 
    symbol="综合损益表",  # ✅ 正确：中文
    indicator="年报"
)
df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])

# 透视转换
profit_pivot = df_profit.pivot(
    index='REPORT_DATE', 
    columns='ITEM_NAME', 
    values='AMOUNT'
).reset_index()
```

---

## 📊 使用示例

### 示例1：计算单个股票

```python
from roic_calculator import calculate_roic

# 计算茅台的 ROIC
df = calculate_roic('A股', 'SH600519', years=5)
print(df[['年份', 'ROIC', 'NOPAT', '投入资本', '净利润']])
```

输出：
```
   年份   ROIC  NOPAT   投入资本   净利润
0  2020  37.87 498.51  1316.30  495.23
1  2021  38.48 558.87  1452.52  557.21
2  2022  44.63 655.09  1467.73  653.76
3  2023  50.15 775.56  1546.43  775.21
4  2024  48.88 893.72  1828.27  893.35
```

---

### 示例2：对比三家公司

```python
from roic_calculator import calculate_roic

# 计算三家公司
stocks = [
    ('A股', 'SH600519', '茅台'),
    ('港股', '00700', '腾讯'),
    ('美股', 'PDD', 'PDD')
]

results = []
for market, code, name in stocks:
    df = calculate_roic(market, code, years=1)  # 获取最新一年
    if len(df) > 0:
        latest = df.iloc[-1]
        results.append({
            '公司': name,
            '市场': market,
            'ROIC': latest['ROIC'],
            '净利润': latest['净利润'],
            '营业收入': latest.get('营业总收入') or latest.get('营业收入', 0)
        })

import pandas as pd
df_compare = pd.DataFrame(results)
print(df_compare)
```

---

### 示例3：导出到 Excel

```python
from roic_calculator import calculate_roic

# 获取数据
df = calculate_roic('A股', 'SH600519', years=5)

# 导出到 Excel
df.to_excel('moutai_roic.xlsx', index=False)
print("✅ 已导出到 moutai_roic.xlsx")
```

---

### 示例4：生成报告

```python
from roic_calculator import calculate_roic
import pandas as pd

# 获取三家公司的数据
df_moutai = calculate_roic('A股', 'SH600519', years=5)
df_tencent = calculate_roic('港股', '00700', years=5)
df_pdd = calculate_roic('美股', 'PDD', years=5)

# 生成 markdown 报告
md_content = """# ROIC 分析报告

## 茅台（A股：SH600519）

"""
md_content += df_moutai.to_markdown(index=False)
md_content += """

## 腾讯（港股：00700）

"""
md_content += df_tencent.to_markdown(index=False)
md_content += """

## PDD（美股：PDD）

"""
md_content += df_pdd.to_markdown(index=False)

# 保存报告
with open('roic_report.md', 'w', encoding='utf-8') as f:
    f.write(md_content)

print("✅ 报告已生成：roic_report.md")
```

---

## 🔍 数据验证

### A股验证

```python
import akshare as ak
import pandas as pd

# 获取利润表
df_profit = ak.stock_profit_sheet_by_yearly_em(symbol='SH600519')
df_profit['REPORT_DATE'] = pd.to_datetime(df_profit['REPORT_DATE'])

# 获取2020年数据
profit_2020 = df_profit[df_profit['REPORT_DATE'].dt.year == 2020].iloc[0]

# 验证：营业利润 + 营业外收入 - 营业外支出 = 利润总额
operate_profit = profit_2020['OPERATE_PROFIT']
nonoperate_income = profit_2020.get('NONOPERATING_INCOME', 0)
nonoperate_expense = profit_2020.get('NONBUSINESS_EXPENSE', 0)
total_profit = profit_2020['TOTAL_PROFIT']

print(f"营业利润：{operate_profit/100000000:.2f} 亿元")
print(f"利润总额：{total_profit/100000000:.2f} 亿元")
print(f"验证：{operate_profit/100000000:.2f} + {nonoperate_income/100000000:.2f} - {nonoperate_expense/100000000:.2f} = {total_profit/100000000:.2f}")
```

---

## 📝 常见问题

### Q1：为什么 A股 ROIC 计算结果偏低？

**A：** 可能使用了错误的营业利润字段。请检查：
- ✅ 使用 `OPERATE_PROFIT`（正确的营业利润）
- ❌ 不要使用 `OPERATE_INCOME`（错误的营业利润）

---

### Q2：为什么港股 ROIC 计算失败？

**A：** 可能是债务字段名称错误。请检查：
- ✅ 使用"短期贷款"、"长期贷款"
- ❌ 不要使用"短期借款"、"长期借款"

---

### Q3：为什么美股接口报错"请输入正确的 symbol 参数"？

**A：** symbol 参数必须使用中文：
- ✅ `symbol="综合损益表"`（正确）
- ❌ `symbol="利润表"`（错误）
- ❌ `symbol="Income Statement"`（错误）

---

### Q4：为什么现金数据为 0？

**A：** 可能使用了错误的现金字段：
- A股：使用 `MONETARYFUNDS`（货币资金），不是 `END_CASH_EQUIVALENTS`
- 港股：使用 `现金及等价物`
- 美股：使用 `现金及现金等价物` 或 `Cash and cash equivalents`

---

### Q5：如何判断计算结果是否正确？

**A：** 验证以下指标：
1. 营业利润率（营业利润 / 营业收入）应该在合理范围内（茅台约 60-70%）
2. 税率（所得税 / 利润总额）应该在 10-30% 之间
3. ROIC 应该在 0-100% 之间（茅台可能更高，因为现金充裕）

---

## 📚 参考资料

- AkShare 官方文档：https://akshare.akfamily.xyz/
- 财务报表接口文档：`../apis/stock_profit_sheet_by_yearly_em.txt`
- 港股接口文档：`../apis/stock_financial_hk_report_em.txt`
- 美股接口文档：`../apis/stock_financial_us_report_em.txt`

---

## 📧 反馈与贡献

如有问题或建议，请联系小叶。

---

**祝使用愉快！** 🎉