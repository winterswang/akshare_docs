# AkShare API 文档与 Skills 生成工具

本项目用于自动下载、解析 AkShare 的 API 文档，并生成适用于 AI Agent 的 Skills 定义（JSON Schema 格式）。

## 📁 项目结构

```
akshare_docs/
├── README.md           # 说明文档
├── run.py              # 主程序入口
├── requirements.txt    # 依赖列表
├── apis_update.py      # 文档下载与解析脚本
├── generate_skills.py  # Skills 生成脚本
├── apis/               # [自动生成] 存放解析后的 API 文档 (.txt)
├── docs/               # [自动生成] 存放汇总文档和 Skills 定义
│   ├── skills.json     # OpenAI Function Calling 格式的工具定义
│   └── summary.md      # API 汇总列表
└── data/               # [自动生成] 临时数据目录
```

## 🚀 快速开始

### 1. 安装依赖

确保你的 Python 版本 >= 3.7。

```bash
pip install -r requirements.txt
```

### 2. 运行工具

直接运行 `run.py` 即可完成所有工作：

```bash
python run.py
```

程序将自动执行以下步骤：
1. **下载最新文档**：从 AkShare 官网下载最新的 API 说明。
2. **解析文档**：将文档拆分为独立的 `.txt` 文件存放在 `apis/` 目录下。
3. **生成清单**：生成 `apis/manifest.json` 索引文件。
4. **生成 Skills**：根据解析结果，生成 `docs/skills.json`，可直接用于 LangChain 或 OpenAI Assistant。

## 📖 产物说明

### 1. API 文档 (`apis/*.txt`)
每个 API 接口都有一个独立的文本文件，包含接口名称、描述、输入参数和输出参数说明。
例如 `apis/stock_zh_a_hist.txt` 包含了 A 股历史行情接口的详细说明。

### 2. Skills 定义 (`docs/skills.json`)
这是一个标准的 JSON 文件，符合 OpenAI Function Calling 格式。
你可以将其加载到你的 AI Agent 中，使其具备查询股市数据的能力。

**示例格式：**
```json
[
  {
    "type": "function",
    "function": {
      "name": "stock_zh_a_hist",
      "description": "获取A股历史行情数据...",
      "parameters": {
        "type": "object",
        "properties": {
          "symbol": { "type": "string", "description": "股票代码" },
          ...
        }
      }
    }
  }
]
```

### 3. 汇总文档 (`docs/summary.md`)
包含了所有已解析 API 的列表和简要说明，方便人类阅读和检索。

## 🛠️ 常见问题

**Q: 运行报错 `ModuleNotFoundError`?**
A: 请确保已运行 `pip install -r requirements.txt` 安装所有依赖。

**Q: 下载速度慢？**
A: 文档源文件托管在 AkShare 官网，取决于网络状况。脚本内置了超时重试机制。

**Q: 如何在 LangChain 中使用？**
A: 你可以编写一个加载器读取 `docs/skills.json`，并将其转换为 LangChain 的 `StructuredTool` 对象列表。
