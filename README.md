# AkShare Financial Data Service

本项目提供了一套**标准化、高容错、业务导向**的金融数据服务层 (`akshare_service`)，屏蔽了底层 AkShare 接口的复杂性（如字段差异、异常处理、代理问题），为上层应用（如 AI Agent、量化回测系统）提供统一的数据获取能力。

## 🌟 核心能力 (Core Skills)

### 1. 财务分析 (Finance Skills)
> 模块路径: `akshare_service.skills.finance`

提供跨市场（A股/港股/美股）的标准化财务指标计算能力。

| 函数名 | 描述 | 支持市场 | 备注 |
|---|---|---|---|
| `calculate_roic(market, code, years)` | 计算投入资本回报率 (ROIC) | A股/港股/美股 | 自动处理不同市场的报表字段映射（如"营业利润" vs "经营溢利"） |
| `calculate_roic_a_share` | A股 ROIC 计算 | A股 | 基于东财年报数据 |
| `calculate_roic_hk` | 港股 ROIC 计算 | 港股 | 基于东财港股年报 |
| `calculate_roic_us` | 美股 ROIC 计算 | 美股 | 基于东财美股综合损益表 |

### 2. 市场行情 (Market Skills)
> 模块路径: `akshare_service.skills.market`

提供统一的行情获取接口，内置多源灾备机制（Fallback）。

| 函数名 | 描述 | 支持市场 | 备注 |
|---|---|---|---|
| `get_current_price(market, code)` | 获取实时行情 (Quote) | A股/港股/美股 | 返回统一格式：代码、名称、最新价、涨跌幅、市值、PE/PB |
| `get_history_price(market, code, ...)` | 获取历史 K 线 (History) | A股/港股/美股 | 自动处理复权 (qfq/hfq)，内置多数据源切换 (EastMoney -> Sina) |

### 3. 新闻资讯 (News Skills)
> 模块路径: `akshare_service.skills.news`

提供个股和市场的实时资讯。

| 函数名 | 描述 | 支持市场 | 备注 |
|---|---|---|---|
| `get_stock_news(market, code, limit)` | 获取个股新闻 | A股 | 自动清洗列名，返回标准化字段 (title, url, publish_time) |
| `get_market_news(limit)` | 获取市场快讯 | 全市场 | 集成财联社电报等多个数据源 |

---

## 🚀 快速集成 (Integration)

### 安装
确保项目在 `PYTHONPATH` 中，或直接将 `akshare_docs` 目录放入你的项目中。

```bash
pip install akshare pandas requests
```

### 调用示例

```python
from akshare_docs.akshare_service.skills.finance import calculate_roic
from akshare_docs.akshare_service.skills.market import get_current_price, get_history_price
from akshare_docs.akshare_service.skills.news import get_stock_news

# 1. 获取茅台实时行情
quote = get_current_price(market='A股', code='600519')
print(f"茅台最新价: {quote['price']}")

# 2. 计算茅台 ROIC
df_roic = calculate_roic(market='A股', code='SH600519', years=3)
print(df_roic)

# 3. 获取个股新闻
news = get_stock_news(market='A股', code='600519')
for n in news:
    print(n['title'])
```

## 🛠️ 架构设计

```
akshare_docs/
├── akshare_service/        # [核心] 服务层
│   ├── skills/             # 业务能力实现
│   │   ├── finance.py      # 财务分析 (ROIC等)
│   │   ├── market.py       # 行情数据 (Quote/History)
│   │   └── news.py         # 新闻资讯
│   └── infra/              # 基础设施
│       └── client.py       # 统一客户端 (代理处理、异常捕获)
├── qa/                     # [质量] 巡检与监控
│   ├── test_apis.py        # 接口可用性测试
│   └── ...
├── scripts/                # [维护] 文档更新脚本
├── apis/                   # API 定义 (自动生成)
└── docs/                   # 文档
```

## ⚠️ 注意事项

1. **网络代理**: 
   - 本项目内置了 `robust_api` 装饰器，会自动处理常见的网络异常。
   - 如果遇到 `ProxyError`，请检查你的系统代理设置，或确保 `push2.eastmoney.com` 等域名在白名单中。

2. **数据源**:
   - 优先使用 **东方财富 (EastMoney)** 接口。
   - 备用数据源包括 **新浪财经 (Sina)** 等。
   - 接口调用频率受限，请勿高频并发调用。
