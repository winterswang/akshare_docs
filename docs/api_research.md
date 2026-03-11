# 财务数据 API 调研报告

## 一、免费开源方案

### 1. AkShare（当前使用）
- **优点**：完全免费、开源、接口丰富、社区活跃
- **缺点**：无官方支持、API 不稳定、可能被限速
- **适用场景**：个人研究、低频调用

### 2. TuShare
- **网址**：https://tushare.pro
- **优点**：
  - 数据质量高、接口稳定
  - 支持 A股、港股、美股、期货、外汇
  - 有积分制度，普通用户每分钟 200 次请求
- **缺点**：
  - 需要注册获取 token
  - 部分高级数据需要积分
- **推荐指数**：⭐⭐⭐⭐⭐

**示例代码**：
```python
import tushare as ts
pro = ts.pro_api('your_token')

# 获取利润表
df = pro.income(ts_code='300760.SZ', start_date='20200101', end_date='20241231')

# 获取资产负债表
df = pro.balancesheet(ts_code='300760.SZ')

# 获取现金流量表
df = pro.cashflow(ts_code='300760.SZ')

# 获取财务指标
df = pro.fina_indicator(ts_code='300760.SZ')
```

### 3. Baostock
- **网址**：http://baostock.com
- **优点**：
  - 完全免费、无需注册
  - 数据来源：证券宝
  - 支持历史 K 线、财务数据
- **缺点**：
  - 数据更新较慢
  - 接口较少
- **推荐指数**：⭐⭐⭐⭐

**示例代码**：
```python
import baostock as bs

# 登录
lg = bs.login()

# 获取利润表
rs = bs.query_profit_data(code="sz300760", year=2024, quarter=4)

# 获取资产负债表
rs = bs.query_balance_data(code="sz300760", year=2024, quarter=4)

# 获取现金流量表
rs = bs.query_cash_flow_data(code="sz300760", year=2024, quarter=4)
```

---

## 二、专业付费方案

### 1. Wind（万得）
- **网址**：https://www.wind.com.cn
- **优点**：
  - 国内金融数据标准
  - 数据最全、更新最快
  - 支持 Excel 插件、API
- **缺点**：
  - 价格昂贵（年费数万至数十万）
  - 需要签订合同
- **适用场景**：机构投资者、专业研究员

### 2. 同花顺 iFinD
- **网址**：https://www.10jqka.com.cn
- **优点**：
  - 数据全面、更新及时
  - 价格相对 Wind 较低
  - 支持 Python API
- **缺点**：
  - 年费约 1-3 万
  - 需要授权

### 3. 东方财富 Choice
- **网址**：https://choice.eastmoney.com
- **优点**：
  - 价格适中（年费约 5000-20000）
  - 数据来源：东方财富
  - 支持 Python API
- **缺点**：
  - 部分数据不如 Wind 全面

---

## 三、量化平台数据

### 1. 聚宽 JQData
- **网址**：https://www.joinquant.com
- **优点**：
  - 免费版每天 100 万条数据
  - 专业版年费约 3000 元
  - 支持财务数据、行情数据
- **推荐指数**：⭐⭐⭐⭐

### 2. RiceQuant
- **网址**：https://www.ricequant.com
- **优点**：
  - 免费版有限制
  - 专业版年费约 5000 元

---

## 四、推荐方案

### 个人研究（免费）
| 优先级 | 方案 | 说明 |
|--------|------|------|
| 1 | TuShare | 数据质量高，稳定性好 |
| 2 | Baostock | 完全免费，备用方案 |
| 3 | AkShare | 当前方案，补充数据 |

### 专业需求（付费）
| 预算 | 推荐方案 |
|------|----------|
| 3000-5000元/年 | 聚宽 JQData 专业版 |
| 5000-20000元/年 | 东方财富 Choice |
| >30000元/年 | Wind / 同花顺 iFinD |

---

## 五、集成建议

### 添加 TuShare 作为备选数据源

```python
# akshare_service/skills/tushare_adapter.py

import tushare as ts

class TushareAdapter:
    def __init__(self, token: str):
        self.pro = ts.pro_api(token)
    
    def get_financial_summary(self, code: str, years: int = 5):
        """使用 TuShare 获取财务数据"""
        ts_code = f"{code}.SZ" if code.startswith(('0', '3')) else f"{code}.SH"
        
        # 获取财务指标
        df = self.pro.fina_indicator(ts_code=ts_code)
        
        # 转换为标准格式
        ...
```

---

## 六、下一步行动

1. **注册 TuShare**：https://tushare.pro 获取免费 token
2. **添加 TuShare 适配器**：作为备选数据源
3. **优化缓存策略**：增加缓存时间
4. **添加数据源优先级**：TuShare → AkShare → Baostock

---

*调研时间: 2026-03-10*