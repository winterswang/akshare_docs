# AkShare Skills Layer (akshare_docs)

## 📌 项目定位 (Project Positioning)
**金融数据能力层 (Financial Data Skill Layer)**

本项目旨在为上层应用（如 LLM Agent、量化交易系统）提供 **标准化、高可用、业务导向** 的金融数据服务。它屏蔽了底层 `AkShare` 接口的复杂性（如字段差异、市场差异、不稳定性），让大模型只需关注“我要查茅台的 ROIC”，而不需要知道“我要调用 `stock_profit_sheet_by_yearly_em` 还是 `stock_financial_hk_report_em`”。

## 🏗️ 架构设计 (Architecture)

```mermaid
graph TD
    User[LLM Agent / User] --> SkillsLayer[Skills Layer (akshare_docs)]
    
    subgraph SkillsLayer
        direction TB
        UnifiedInterface[统一接口 (Unified Interface)]
        BusinessLogic[业务逻辑 (Business Logic)]
        DataValidation[数据验证 (Validation)]
    end
    
    SkillsLayer --> RawAPIs[底层 AkShare API]
    SkillsLayer --> Cache[本地缓存 (Cache)]
    
    subgraph QualityAssurance [质量保障体系]
        AutoTest[自动化测试 (Test)]
        Monitor[巡检监控 (Monitor)]
        Report[可视化报告 (Report)]
    end
```

## 🛠️ 核心模块 (Core Modules)

### 1. `skills/` (业务能力层)
存放面向业务的高级函数，供 Agent 直接调用。
- **`finance.py`**: 财务分析能力 (e.g., `calculate_roic`, `get_pe_pb`, `get_income_statement`)
- **`market.py`**: 行情数据能力 (e.g., `get_current_price`, `get_hist_price`, `get_market_status`)
- **`news.py`**: 资讯获取能力 (e.g., `get_stock_news`, `get_market_news`)
- **`fund.py`**: 基金分析能力

### 2. `infra/` (基础设施层)
- **`client.py`**: 统一的 AkShare 调用客户端，处理重试、超时、代理。
- **`cache.py`**: 数据缓存机制。
- **`logger.py`**: 统一日志。

### 3. `qa/` (质量保障层) - *原 scripts 目录升级*
- **`test_apis.py`**: API 可用性巡检。
- **`report_generator.py`**: 生成巡检报告。
- **`notify.py`**: 飞书/钉钉报警。

## 🚀 快速开始 (Quick Start)

### 作为工具库使用
```python
from akshare_docs.skills.finance import calculate_roic

# 一行代码计算多市场 ROIC，无需关心底层差异
df = calculate_roic(market='A股', code='600519')
```

### 运行巡检
```bash
python -m akshare_docs.qa.test_apis
```

## 📝 目录结构 (Directory Structure)
```
akshare_docs/
├── apis/               # 原始 API 定义 (自动生成)
├── config/             # 配置文件
├── docs/               # 文档与 Schema
├── akshare_service/    # [Package] 核心代码包
│   ├── __init__.py
│   ├── skills/         # 业务能力实现
│   │   ├── finance.py
│   │   └── market.py
│   └── infra/          # 基础设施
├── scripts/            # 维护脚本 (更新文档、生成 Schema)
├── tests/              # 单元测试
└── run.py              # 入口
```
