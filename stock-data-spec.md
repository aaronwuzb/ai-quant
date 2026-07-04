# 股票数据规范化取数规范 (Stock Data Spec)

> 版本: v2.0 | 创建: 2026-07-04 | 更新: 2026-07-04 | 适用范围: 全市场股票数据获取与分析

---

## 1. 概述

本规范定义了标准化的股票数据获取流程、字段标准、输出格式与命名约定。
所有股票数据相关工作均应遵循本 spec，确保数据一致性、可复现性和可追溯性。

## 2. 股票识别规范

每只目标股票需统一登记以下标识字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| `code` | 数字代码（A股6位/HK股5位） | `688981` / `00981` |
| `full_code` | 全代码（含后缀） | `688981.SH` / `00981.HK` |
| `name` | 中文简称 | 中芯国际 |
| `market` | 市场: SH/SZ/HK/US | `SH` |
| `board` | 板块: 主板/科创板/创业板/港股主板 | `科创板` |
| `industry` | 申万一级行业 | 电子 |
| `sub_industry` | 细分领域 | 集成电路制造 |
| `is_ah` | 是否 AH 双重上市 | true/false |
| `linked_code` | AH 关联代码 | 00981.HK |
| `currency` | 计价货币 | CNY / HKD |
| `tags` | 特性标签 | 半导体龙头/AH溢价/高股息/蓝筹 |

### 2.1 本次目标股票清单

#### ID: SMIC — 中芯国际
```yaml
a_share:
  code: "688981"
  full_code: "688981.SH"
  market: SH
  board: 科创板
  currency: CNY
h_share:
  code: "00981"
  full_code: "00981.HK"
  market: HK
  board: 港股主板
  currency: HKD
industry: 电子
sub_industry: 集成电路制造
tags: [半导体龙头, AH双重上市, 晶圆代工]
ah_ratio_note: 港股按 0.91 汇率折算人民币后进行 AH 溢价计算
```

#### ID: BYD — 比亚迪
```yaml
a_share:
  code: "002594"
  full_code: "002594.SZ"
  market: SZ
  board: 主板
  currency: CNY
h_share:
  code: "01211"
  full_code: "01211.HK"
  market: HK
  board: 港股主板
  currency: HKD
industry: 汽车
sub_industry: 新能源整车/动力电池
tags: [新能源龙头, AH双重上市, 高成长]
ah_ratio_note: 港股按 0.91 汇率折算人民币后进行 AH 溢价计算
```

#### ID: YANGTZE — 长江电力
```yaml
a_share:
  code: "600900"
  full_code: "600900.SH"
  market: SH
  board: 主板
  currency: CNY
h_share: null
industry: 公用事业
sub_industry: 水力发电
tags: [高股息, 蓝筹, 防御型, 纯A股]
ah_ratio_note: 无港股上市，不计算 AH 溢价
```

---

## 3. 数据维度层级

采用 L1-L4 分层体系，每次取数需明确指定层级范围。

### 3.1 L1 — 基础行情数据 (Basic Market Data)

**用途**: 日线 K 线分析、基础走势、归一化对比

**字段标准** (JSON):
```json
[
  {
    "date": "YYYY-MM-DD",
    "open": 0.0,
    "close": 0.0,
    "high": 0.0,
    "low": 0.0,
    "volume": 0,
    "amount": 0.0
  }
]
```

**字段定义**:

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| `date` | string | - | 交易日，格式 YYYY-MM-DD |
| `open` | float | 元 | 开盘价（前复权，如适用） |
| `close` | float | 元 | 收盘价（前复权，如适用） |
| `high` | float | 元 | 最高价 |
| `low` | float | 元 | 最低价 |
| `volume` | int | 手(A股) / 股(港股) | 成交量 |
| `amount` | float | 元 | 成交额 |

**取数接口**:

| 优先级 | 数据源 | A股 API | 港股 API | 特点 |
|--------|--------|---------|----------|------|
| 1 (首选) | **akshare** | `stock_zh_a_daily(symbol, adjust="qfq")` | `stock_hk_daily(symbol, adjust="qfq")` | 免费、无需 Token、数据单位接近标准 |
| 2 (备选) | Tushare | `pro.daily(ts_code, ...)` | `pro.hk_daily(ts_code, ...)` | 需 Token、有频率限制、amount 单位需转换 |
| 3 (兜底) | 腾讯自选股 | westock-data skill | westock-data skill | 通过 WorkBuddy Skill 调用 |

**akshare API 详细说明**:

```
# A股 — Sina 数据源
ak.stock_zh_a_daily(symbol="sh688981" / "sz002594", adjust="qfq")

返回字段映射:
  date              → date   (YYYY-MM-DD, 直接使用)
  open / close      → open / close (元, 直接使用)
  high / low        → high / low   (元, 直接使用)
  volume            → volume (股 → 需 /100 转为 手)
  amount            → amount (元, 直接使用)

# 港股 — Sina 数据源
ak.stock_hk_daily(symbol="00981" / "01211", adjust="qfq")

返回字段映射:
  date              → date   (YYYY-MM-DD, 直接使用)
  open / close      → open / close (港元, 直接使用)
  high / low        → high / low   (港元, 直接使用)
  volume            → volume (股, 直接使用)
  amount            → amount (港元, 直接使用)
```

**Tushare API 详细说明** (备选):

```
# A股
pro.daily(ts_code="688981.SH", start_date="...", end_date="...")

返回字段映射:
  trade_date        → date   (YYYYMMDD → YYYY-MM-DD)
  open/high/low/close →      (元, 直接使用)
  vol               → volume (手, 直接使用)
  amount            → amount (千元 → **需 ×1000 转为元**)

# 港股
pro.hk_daily(ts_code="00981.HK", start_date="...", end_date="...")
  (同上, amount 同样需 ×1000)
```

### 3.1.1 单位标准化规则

所有数据入库前必须统一为以下标准单位。不同数据源的原始单位不同，**必须在获取阶段完成转换**：

| 字段 | 标准单位 | akshare 原始 | akshare 转换 | Tushare 原始 | Tushare 转换 |
|------|----------|-------------|-------------|-------------|-------------|
| price (OHLC) | 元 / 港元 | 元 / 港元 | 无需转换 | 元 | 无需转换 |
| volume (A股) | **手** | **股** | **÷ 100** | **手** | 无需转换 |
| volume (港股) | **股** | **股** | 无需转换 | — | — |
| amount | **元** / **港元** | 元 / 港元 | 无需转换 | **千元** | **× 1000** |

**强制规则**:
- `fetch_data.py` 是唯一的数据入库入口，单位转换在此完成
- 禁止手动编辑 JSON/CSV 数据文件
- 质量检查 #9 (成交额量级验证) 可自动发现单位转换错误

### 3.1.2 除权除息标注

在前复权 (qfq) 数据中，除权除息日会出现价格跳变，属于正常现象：

1. **检测方法**: 遍历数据，检测单日 `abs((open[t] - close[t-1]) / close[t-1]) > 30%`
2. **JSON 标注**: 在对应日期记录中添加可选字段 `"adjust_flag": "ex_right"`
3. **面板标注**: HTML 面板中 K 线图上方标注除权日橙色 "×" 标记
4. **统计注明**: 面板免责声明中注明"含除权调整"

示例 (比亚迪 2025-07-29):
  前一日收盘价: ~337 元 (前复权)
  除权日开盘价: ~112 元 (前复权, 已调整)
  → 跳变约 -67%, 典型的送转股除权

### 3.2 L2 — 增强市场数据 (Enhanced Market Data)

在 L1 基础上增加：

- **周线/月线**: 同 L1 字段，频率为 weekly/monthly
- **资金流向** (`moneyflow`): 主力净流入、超大单/大单/中单/小单净额
- **融资融券** (`margin`): 融资余额、融券余量
- **沪深港通** (`moneyflow_hsgt`): 北向资金持股、买卖额
- **涨跌停** (`stk_limit`): 涨停价、跌停价

### 3.3 L3 — 基本面数据 (Fundamental Data)

- **财务指标** (`fina_indicator`): ROE、ROA、毛利率、净利率、资产负债率、EPS、每股净资产
- **估值指标**: PE(TTM)、PB、PS(TTM)、股息率
- **利润表/资产负债表/现金流量表** 关键科目
- **股东数据** (`top10_holders`): 前十大股东、股东人数变化

### 3.4 L4 — 事件与特色数据 (Event & Specialty Data)

- **分红送转** (`dividend`): 除权除息日、每股股利、送转比例
- **业绩预告/快报** (`forecast` / `express`)
- **龙虎榜** (`top_list`)
- **限售解禁** (`share_float`)
- **机构调研** (`stk_surv`)
- **AH 溢价率**: 日度 AH 价格比（仅 AH 双重上市股票）

---

## 4. 时间范围预设

| 预设 | 参数 | 说明 |
|------|------|------|
| `1Y` | 近一年 | start = today - 365d, end = today |
| `3Y` | 近三年 | start = today - 3y |
| `5Y` | 近五年 | start = today - 5y |
| `YTD` | 年初至今 | start = Jan 1 of current year |
| `ALL` | 上市以来 | start = ipo_date |
| `CUSTOM` | 自定义 | 手动指定 start/end |

---

## 5. 输出文件标准

### 5.1 命名约定

```
{股票简称}_{代码标识}_{数据描述}.{扩展名}
```

示例:
```
中芯国际_sh688981_近一年数据.json
中芯国际_hk00981_近一年数据.json
中芯国际_AH对比分析面板.html
比亚迪_sz002594_近一年数据.json
长江电力_sh600900_近一年数据.json
```

### 5.2 目录结构

```
{project_root}/
├── stock-data-spec.md              # 本规范文件
├── data/                           # 原始数据目录（可选）
│   ├── {stock_name}_{code}_{period}.json
│   └── {stock_name}_{code}_{period}.csv
├── panels/                         # 分析面板目录（可选）
│   └── {stock_name}_{analysis}.html
└── notebooks/                      # 分析 Notebook（可选）
    └── {stock_name}_分析.ipynb
```

### 5.3 JSON 标准格式

每个数据文件根层级为数组，每个元素为一个交易日对象：

```json
[
  {
    "date": "2025-07-03",
    "open": 85.50,
    "close": 86.20,
    "high": 87.00,
    "low": 84.80,
    "volume": 150000,
    "amount": 12850000.0
  }
]
```

数据按 `date` 升序排列（最早在前）。

### 5.4 CSV 标准格式

使用 UTF-8 编码（CSV 使用 UTF-8-BOM 以确保 Excel 兼容），逗号分隔。

#### JSON 元信息格式 (v2.0)

```json
{
  "_meta": {
    "stock": "中芯国际",
    "code": "sh688981",
    "source": "akshare.stock_zh_a_daily",
    "fetch_time": "2026-07-04T14:20:00",
    "date_range": ["2025-07-04", "2026-07-03"],
    "total_days": 236,
    "adjust": "qfq"
  },
  "data": [
    {"date": "...", "open": 0.0, "close": 0.0, ...}
  ]
}
```

### 5.5 输出一致性验证

每次生成数据文件后，验证以下一致性：

1. JSON 和 CSV 记录数完全一致
2. JSON 可正常 `json.load()` 解析
3. CSV 可正常 `csv.DictReader()` 读取
4. 所有价格值精确到小数点后 2 位 (`round(x, 2)`)
5. amount 值精确到小数点后 2 位
6. volume 为整数 (`int`)
7. 日期格式统一为 YYYY-MM-DD (10 位固定长度)
8. 数据按 `date` 升序排列

### 5.6 工具链标准 (v2.0)

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `fetch_data.py` | 统一数据获取 | akshare API | JSON + CSV |
| `gen_panels.py` | 统一面板生成 | JSON 文件 | HTML 面板 |
| `qc_check.py` | 自动化质量检查 | JSON 文件 | `qc_report.json` |

**禁止**直接手动编辑数据文件。所有数据变更必须通过 `fetch_data.py` 重新获取。

---

## 6. 质量检查规则

每条数据获取完成后，必须执行以下检查：

| # | 检查项 | 规则 | 处理 |
|---|--------|------|------|
| 1 | 日期连续性 | 实际天数 ≥ 预期交易日的 95% | 低于阈值则报告缺失率 |
| 2 | 价格逻辑 | low ≤ open/close ≤ high | 如有违反，标注异常并回溯原始数据 |
| 3 | 成交量非负 | volume ≥ 0 | 负数记录需追溯修正 |
| 4 | 价格跳空 | abs((open - pre_close)/pre_close) > 15% | 标注为异常波动，检查是否为除权除息 |
| 5 | 复权一致性 | 确保所有价格统一为前复权 (qfq) | 不一致则重新获取 |
| 6 | 数据完整性 | 实际天数 ≥ 预期交易日的 95% | 低于阈值则报告缺失率 |
| 7 | AH 对齐 | AH 双重上市股票按共同交易日对齐 | 记录独立交易日天数 |
| **8** | **价格量级合理性** | A股 0.1~10000 元, 港股 0.01~10000 | **超出范围标记 WARN** |
| **9** | **成交额量级验证** | A股日均 10^6~10^11 元, 港股日均 10^5~10^10 | **量级异常提示单位转换错误** |

### 6.1 停牌处理

- 停牌期间不产生数据行（不做填充）
- 在分析中如需连续时间轴，使用前收盘价前向填充（标注为估算值）

### 6.2 自动化质量检查 (Auto QC)

质量检查脚本 `qc_check.py` 应在每次数据入库后自动运行：

**检查项**:
- 执行全部 9 项质量检查规则
- 验证 JSON 与 CSV 一致性 (行数、字段值)
- 自动检测 AH 股票的重叠交易日

**输出**: `qc_report.json`

```json
{
  "_meta": {
    "check_date": "2026-07-04T14:30:00",
    "spec_version": "v2.0",
    "total_files": 5
  },
  "results": {
    "中芯国际_sh688981": {
      "name": "中芯国际",
      "code": "sh688981",
      "market": "A",
      "total_days": 236,
      "overall": "pass",
      "checks": {
        "1_dates": {"name": "日期连续性", "status": "pass", "detail": "236/242 (97.5%)"},
        "2_price_logic": {"name": "价格逻辑", "status": "pass", "detail": "全部通过"},
        ...
      }
    }
  }
}
```

**运行方式**: `python qc_check.py`

---

## 7. 工作流程检查清单

每次取数任务按此清单逐项完成：

```
□ Step 1 — 股票识别
  □ 确认代码、市场、行业
  □ 确认是否 AH 双重上市及关联代码
  □ 填写 tags 标签

□ Step 2 — 维度选择
  □ 确定数据层级 (L1 / L1+L2 / 全层级)
  □ 列出所需字段清单

□ Step 3 — 参数设定
  □ 指定时间范围预设或自定义日期
  □ 确认复权方式 (默认前复权 qfq)
  □ 确认频度 (日/周/月)

□ Step 4 — 数据获取
  □ A 股: akshare.stock_zh_a_hist()
  □ 港股（如有）: akshare.stock_hk_hist()
  □ 备份: Tushare / 腾讯自选股

□ Step 5 — 质量检查
  □ 执行 7 项质量检查规则
  □ 输出质量报告摘要
  □ 异常数据标注与说明

□ Step 6 — 标准化输出
  □ 生成 JSON 文件（命名: {股票简称}_{代码}_{描述}.json）
  □ 生成 CSV 文件（命名: {股票简称}_{代码}_{描述}.csv）
  □ 生成 HTML 分析面板（命名: {股票简称}_{描述}.html）
  □ 验证文件可正常打开与解析
```

---

## 8. 分析面板标准

### 8.1 单股票日线面板

- K 线图 + 成交量（双面板布局，Plotly Candlestick）
- 涨跌幅: 红涨绿跌（中国市场惯例）
- 标注: 最高价日期、最低价日期
- 基本统计: 起始价、最新价、涨跌幅、波动率、交易天数
- 高度: 600px

### 8.2 AH 对比面板（仅双重上市股票）

- 归一化价格走势对比（基准=100）
- AH 溢价率柱状图
- 双 K 线并排对比
- 日收益率分布对比
- 溢价率统计: 均值、最高、最低、标准差

### 8.3 面板技术规格

- 使用 Plotly.js (CDN: cdnjs)
- 模板: plotly_white
- 字体: 系统默认 sans-serif
- 不需要外部 CSS 文件，样式内嵌

---

## 9. 本次取数任务配置

### 任务: 典型股票数据批次 — Batch 001 (v2.0)

| 股票 | ID | A股代码 | 港股代码 | 层级 | 时间 | 输出 |
|------|-----|---------|----------|------|------|------|
| 中芯国际 | SMIC | 688981.SH | 00981.HK | L1 | 1Y | JSON + CSV + HTML 面板 |
| 比亚迪 | BYD | 002594.SZ | 01211.HK | L1 | 1Y | JSON + CSV + HTML 面板 |
| 长江电力 | YANGTZE | 600900.SH | - | L1 | 1Y | JSON + CSV + HTML 面板 |

**数据获取结果** (2026-07-04):

| 股票 | 代码 | 实际天数 | 日期范围 | 起始价 | 最新价 | 涨跌幅 |
|------|------|----------|----------|--------|--------|--------|
| 中芯国际 A | sh688981 | 236 | 2025-07-04~2026-07-03 | ¥85.80 | ¥140.31 | +63.53% |
| 中芯国际 H | hk00981 | 245 | 2025-07-04~2026-07-03 | HK$43.95 | HK$77.60 | +76.56% |
| 比亚迪 A | sz002594 | 242 | 2025-07-04~2026-07-03 | ¥109.03 | ¥88.47 | -18.86% |
| 比亚迪 H | hk01211 | 245 | 2025-07-04~2026-07-03 | HK$120.92 | HK$84.10 | -30.45% |
| 长江电力 A | sh600900 | 242 | 2025-07-04~2026-07-03 | ¥29.19 | ¥27.05 | -7.33% |

**数据处理**:
- 数据源: akshare (Sina)
- 复权方式: 前复权 (qfq)
- 质量检查: 全部 5 个文件 PASS
- 面板生成: 5 个 HTML (含 2 个 AH 对比)

**特殊说明**:
- 中芯国际、比亚迪: 已获取完整 A+H 数据，生成 AH 对比面板
- 长江电力: 仅 A 股，生成单股票日线面板
- 比亚迪 2025-07-29 存在除权跳变（前复权价格从 ~337 跳至 ~112），面板中已标注
- 时间区间: 2025-07-04 ~ 2026-07-03

---

## 10. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.0 | 2026-07-04 | 重大升级: 新增数据源配置标准 (akshare/Tushare API 映射)、单位标准化规则 (volume 股→手, amount 千元→元)、除权除息标注规则、自动化质量检查 (#8-9 + qc_report.json)、输出一致性验证、工具链标准化 (fetch_data.py / gen_panels.py / qc_check.py)；改用 akshare Sina 源替代东方财富；修复 amount 单位 Bug 和长江电力数据缺失问题 |
| v1.0 | 2026-07-04 | 初始版本，定义 L1-L4 数据层级、字段标准、命名约定、7 项质量规则 |
