---
name: stock-data-fetcher
description: |
  股票数据规范化取数工具链。支持 A 股/港股 L1 日线数据的获取、JSON/CSV 输出、
  Plotly 交互式 HTML 面板生成、以及 9 项自动化质量检查。基于 akshare (Sina 源)。
  触发词：股票数据、取数、获取股票、L1 数据、行情数据、股票面板、K 线分析、
  AH 对比、质量检查、fetch stock data、stock panel、OHLCV。
agent_created: true
---

# 股票数据规范化取数 (Stock Data Fetcher)

## 概述

此 skill 提供标准化的股票 L1 基础行情数据获取、输出和可视化工作流。
基于项目 `stock-data-spec.md` v2.0 规范，统一使用 akshare (Sina 源) 作为首选数据源。

## 触发条件

当用户请求获取股票日线数据、生成 K 线分析面板、或执行股票数据质量检查时使用此 skill。

典型触发语句：
- "帮我获取 XX 股票的近一年数据"
- "生成 XX 股票的 K 线分析面板"
- "检查股票数据质量"
- "更新所有股票数据"

## 三步工具链

项目根目录下有三个核心脚本，按顺序执行：

```
fetch_data.py  →  gen_panels.py  →  qc_check.py
 (获取数据)        (生成面板)         (质量检查)
```

### Step 1: fetch_data.py — 数据获取

**数据源**: akshare (`stock_zh_a_daily` / `stock_hk_daily`，Sina 源，免费无需 token)

**配置修改点**（`STOCKS` 列表和 `DATE_START`/`DATE_END`）:
```python
STOCKS = [
    {"name": "股票名", "a_symbol": "sh600900", "a_code": "sh600900",
     "h_symbol": "00981", "h_code": "hk00981", "has_h": True, "tags": [...]},
]
```

**单位转换规则**（fetch_data.py 内部自动处理）:
| 字段 | 标准单位 | akshare 原始 | 转换 |
|------|----------|-------------|------|
| A股 volume | 手 | 股 | ÷ 100 |
| 港股 volume | 股 | 股 | 无需转换 |
| amount | 元/港元 | 元/港元 | 无需转换 |

**输出**: `{股票名}_{代码}_近一年数据.json`（含 `_meta` 元信息）+ `.csv`

**⚠️ 运行方式**: 必须在 Windows 上设置 UTF-8 编码：
```bash
PYTHONIOENCODING=utf-8 python fetch_data.py
```

### Step 2: gen_panels.py — 面板生成

读取 JSON 数据文件，自动判断单股票 / AH 双重上市类型，生成 Plotly 交互式 HTML。

**股票配置**（`STOCKS` 字典，与 fetch_data.py 保持同步）:
```python
STOCKS = {
    "股票名": {"a_code": "shXXXXXX", "h_code": "hkXXXXX", "has_h": True},
}
```

**功能亮点**:
- 动态金额单位（万/亿自动切换）
- 除权日自动检测（价格跳变 >30%）并标注
- 单股票面板：6 指标卡片 + K 线图 + 收盘价走势 + 多空/风险分析
- AH 对比面板：归一化价格走势 + AH 溢价率柱状图 + 双 K 线对比

**生成文件**: `{股票名}_K线分析面板.html`、`{股票名}_AH对比分析面板.html`

### Step 3: qc_check.py — 质量检查

对全部 JSON 数据文件执行 9 项自动化检查，输出 `qc_report.json`。

**9 项检查**:
| # | 检查项 | 规则 |
|---|--------|------|
| 1 | 日期连续性 | 实际天数 ≥ 预期的 95% |
| 2 | 价格逻辑 | low ≤ open/close ≤ high |
| 3 | 成交量非负 | volume ≥ 0 |
| 4 | 价格跳空 | abs((open-pre_close)/pre_close) > 15% |
| 5 | 复权一致性 | 统一前复权 (qfq) |
| 6 | 数据完整性 | 实际天数 ≥ 预期的 95% |
| 7 | AH 对齐 | 按共同交易日对齐 |
| 8 | 价格量级合理性 | A股 0.1~10000, 港股 0.01~10000 |
| 9 | 成交额量级验证 | A股 10^6~10^11, 港股 10^5~10^10 |

## 关键约定

### 颜色规范（中国市场：红涨绿跌）
- 涨 (close ≥ open): `#e83939` (红)
- 跌 (close < open): `#2ba350` (绿)
- 收盘价线: `#378add` (蓝)

### 复权方式
统一使用**前复权 (qfq)**。

### AH 溢价计算
汇率: **HKD/CNY = 0.91**
```
溢价率 = (A股收盘价 - 港股收盘价 × 0.91) / (港股收盘价 × 0.91) × 100%
```

### 文件命名
```
{股票简称}_{代码标识}_{数据描述}.{扩展名}
示例: 中芯国际_sh688981_近一年数据.json
      比亚迪_AH对比分析面板.html
```

### JSON 输出格式 (v2.0)
```json
{
  "_meta": {
    "stock": "中芯国际", "code": "sh688981",
    "source": "akshare.stock_zh_a_daily",
    "fetch_time": "2026-07-04T14:20:00",
    "date_range": ["2025-07-04", "2026-07-03"],
    "total_days": 236, "adjust": "qfq"
  },
  "data": [
    {"date": "2025-07-04", "open": 85.80, "close": 86.10,
     "high": 87.00, "low": 84.50, "volume": 252257, "amount": 21664123.00}
  ]
}
```

## 添加新股票

1. 在 `fetch_data.py` 的 `STOCKS` 列表中添加：
   ```python
   {"name": "新股票", "a_symbol": "shXXXXXX", "a_code": "shXXXXXX",
    "h_symbol": "XXXXX", "h_code": "hkXXXXX", "has_h": True, "tags": [...]}
   ```
2. 在 `gen_panels.py` 的 `STOCKS` 字典中同步添加
3. 在 `stock-data-spec.md` 的 2.1 节登记股票信息
4. 在 `qc_check.py` 的 `configs` 列表中添加检查项
5. 按顺序运行三步工具链

## 数据源备选方案

如 akshare (Sina 源) 不可用：

| 优先级 | 数据源 | A股 API | 注意事项 |
|--------|--------|---------|----------|
| 1 | akshare | `stock_zh_a_daily(symbol, adjust="qfq")` | 免费，volume 需 /100 |
| 2 | Tushare MCP | `daily(ts_code)` | 需 Token，amount ×1000（千元→元） |
| 3 | westock-data | WorkBuddy Skill | 通过 Skill 调用 |

## 注意事项

- **禁止**直接手动编辑 JSON/CSV 数据文件，所有变更通过 `fetch_data.py` 重新获取
- Windows 运行 Python 脚本需设置 `PYTHONIOENCODING=utf-8`
- 除权除息日在前复权数据中会出现价格跳变（如比亚迪 2025-07-29），属正常现象
- 港股交易日多于 A 股（约多 5-10 天/年）
- 预期年交易日约 242 天（用于数据完整性阈值计算）
