# 技术指标实验室 — 产品设计文档

> 版本: v1.0 | 日期: 2026-07-04 | 状态: 设计阶段

---

## 1. 产品概述

### 1.1 一句话描述

一个纯前端 HTML 工具，支持多股票切换、四个技术指标参数自由调节、图表实时重绘。

### 1.2 核心价值

当前的 `gen_indicator_panel.py` 脚本每改一次参数就要重新跑 Python → 生成 HTML → 刷新浏览器。新工具把计算全部搬到浏览器端，参数调节即时生效，无需重新生成文件。

### 1.3 目标用户

学习技术指标原理的个人投资者 / 学生，需要直观对比不同参数对指标形态的影响。

---

## 2. 功能范围

### 2.1 V1 功能清单

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 股票选择 | 下拉菜单切换 5 只股票 (A股/港股) | P0 |
| 数据加载 | 从预生成的 CSV 文件读取 OHLCV 数据 | P0 |
| RSI 计算 + 绘图 | 参数: 周期 (默认14), 超买线/超卖线可调 | P0 |
| MACD 计算 + 绘图 | 参数: 快线(12)/慢线(26)/信号线(9) 可调 | P0 |
| 布林带计算 + 绘图 | 参数: 周期(20)/标准差倍数(2.0) 可调 | P0 |
| ATR 计算 + 绘图 | 参数: 周期(14) 可调 | P0 |
| K 线概览图 | 始终展示当前股票的 OHLC + 成交量 | P0 |
| 概要指标卡片 | 顶部 4 张卡片显示最新值 + 信号状态 | P0 |
| 参数滑块 | 每个指标独立 slider + number input | P1 |
| 单指标重绘 | 改变某指标参数时只重绘该图表 | P1 |

### 2.2 明确不做的 (V1)

- 不新增数据源 / 在线 API 拉取
- 不支持自定义指标公式
- 不支持图表导出
- 不支持多股票叠加对比
- 不支持日期范围筛选

---

## 3. 技术架构

### 3.1 核心决策

```
方案: 纯浏览器端计算
语言: HTML + CSS + Vanilla JavaScript (ES6)
可视化: Plotly.js (CDN 加载)
数据: 预生成的 CSV 文件 → 浏览器 fetch() → PapaParse 解析
```

**为什么不用 Python 后端？**
- CSV 数据量极小 (245 行 × 6 列 ≈ 15KB)，浏览器端计算毫无压力
- 零部署，双击 HTML 即可使用
- 参数调节即时生效，无需等待 Python 重新执行

### 3.2 技术栈

| 层级 | 方案 | 理由 |
|------|------|------|
| 图表 | Plotly.js 2.35.3 (CDN) | 与项目现有面板一致 |
| CSV 解析 | Papa Parse 5.x (CDN) | 轻量、流式解析、自动类型转换 |
| 数据计算 | 原生 Array + Math | 245 点 × 4 指标, 原生足够 |
| UI 框架 | 无框架, 原生 DOM | 避免引入 React/Vue 的构建负担 |
| 样式 | 内联 CSS + CSS 变量 | 单文件可维护 |

### 3.3 CDN 依赖

```
plotly.js:  cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.3/plotly.min.js
papaparse:  cdnjs.cloudflare.com/ajax/libs/PapaParse/5.5.2/papaparse.min.js
```

---

## 4. 数据模型

### 4.1 股票注册表 (StockRegistry)

```js
const STOCK_REGISTRY = [
  { id: "sm_hk",   name: "中芯国际",  code: "00981.HK",  csv: "中芯国际_hk00981_近一年数据.csv" },
  { id: "sm_a",    name: "中芯国际",  code: "688981.SH", csv: "中芯国际_sh688981_近一年数据.csv" },
  { id: "byd_a",   name: "比亚迪",    code: "002594.SZ", csv: "比亚迪_sz002594_近一年数据.csv" },
  { id: "byd_hk",  name: "比亚迪",    code: "01211.HK",  csv: "比亚迪_hk01211_近一年数据.csv" },
  { id: "cjdl",    name: "长江电力",  code: "600900.SH", csv: "长江电力_sh600900_近一年数据.csv" },
];
```

### 4.2 运行时数据结构

```
AppState {
  currentStockId: string,
  rawData: Row[],           // CSV 解析后的完整数据
  indicators: {
    rsi:  { values: float[], params: { period:14, overbought:70, oversold:30 } },
    macd: { values: {dif,dea,bar}[], params: { fast:12, slow:26, signal:9 } },
    bb:   { values: {mid,upper,lower,pctB}[], params: { period:20, multiplier:2.0 } },
    atr:  { values: float[], params: { period:14 } }
  }
}
```

### 4.3 指标计算模块签名 (纯函数)

```
computeRSI(closeArr, period)      → rsiArr[]
computeMACD(closeArr, fast,slow,signal) → {dif[], dea[], bar[]}
computeBB(closeArr, period, mult) → {mid[], upper[], lower[], pctB[]}
computeATR(highArr, lowArr, closeArr, period) → atrArr[]
```

所有函数为纯函数，输入数据数组 + 参数 → 输出计算结果数组。不依赖全局状态。

---

## 5. 组件树

```
App
├── Header
│   ├── 标题 "技术指标实验室"
│   └── StockSelector (下拉菜单)
│
├── IndicatorPanel (4 列 grid)
│   ├── ParamCard[RSI]
│   │   ├── Label "RSI"
│   │   ├── Slider: 周期 (2-50, 步长1)
│   │   ├── Slider: 超买线 (50-100, 步长1)
│   │   ├── Slider: 超卖线 (0-50, 步长1)
│   │   └── Button "应用"
│   ├── ParamCard[MACD]
│   │   ├── Slider: 快线 (2-50, 步长1)
│   │   ├── Slider: 慢线 (5-100, 步长1)
│   │   ├── Slider: 信号线 (2-20, 步长1)
│   │   └── Button "应用"
│   ├── ParamCard[Bollinger]
│   │   ├── Slider: 周期 (5-100, 步长1)
│   │   ├── Slider: 标准差倍数 (1.0-4.0, 步长0.1)
│   │   └── Button "应用"
│   └── ParamCard[ATR]
│       ├── Slider: 周期 (2-50, 步长1)
│       └── Button "应用"
│
├── SummaryCards (4 列 grid)
│   ├── MetricCard "收盘价" + 涨跌幅 + 趋势色
│   ├── MetricCard "RSI" + 信号标签
│   ├── MetricCard "MACD" + 金叉/死叉计数
│   └── MetricCard "ATR" + 波动状态
│
└── ChartArea (纵向堆叠)
    ├── Chart[K线]    (始终可见)
    ├── Chart[RSI]    (独立重绘)
    ├── Chart[MACD]   (独立重绘)
    ├── Chart[布林带]  (独立重绘)
    └── Chart[ATR]    (独立重绘)
```

---

## 6. 交互流程

### 6.1 首次加载

```
1. 页面加载 → 默认选中第一只股票 (中芯国际 00981.HK)
2. fetch(CSV) → PapaParse 解析 → 得到 {date, open, high, low, close, volume}[]
3. 用默认参数计算四个指标
4. 渲染 4 张概要卡片 + 5 张图表
```

### 6.2 切换股票

```
1. 用户选择新股票
2. fetch(新CSV) → 解析 → 替换 rawData
3. 保持当前参数不变 → 重新计算全部四个指标
4. 重新渲染全部卡片+图表
```

### 6.3 调节参数

```
1. 用户拖动 RSI 周期滑块 (14 → 7)
2. 点击 "应用" 按钮 或 滑块已带 onChange (debounce 300ms)
3. 调用 computeRSI(closeArr, 7) → 替换 indicators.rsi.values
4. 仅重绘 RSI 图表 + 更新 RSI 概要卡片
5. MACD / BB / ATR 图表不受影响
```

---

## 7. 参数规格

### 7.1 RSI

| 参数 | 默认值 | 范围 | 步长 | 说明 |
|------|--------|------|------|------|
| period | 14 | 2 ~ 50 | 1 | 计算周期 |
| overbought | 70 | 50 ~ 100 | 1 | 超买阈值线 |
| oversold | 30 | 0 ~ 50 | 1 | 超卖阈值线 |

约束: overbought > oversold

### 7.2 MACD

| 参数 | 默认值 | 范围 | 步长 | 说明 |
|------|--------|------|------|------|
| fast | 12 | 2 ~ 50 | 1 | 快线 EMA 周期 |
| slow | 26 | 5 ~ 100 | 1 | 慢线 EMA 周期 |
| signal | 9 | 2 ~ 20 | 1 | DEA 信号线周期 |

约束: fast < slow

### 7.3 Bollinger Bands

| 参数 | 默认值 | 范围 | 步长 | 说明 |
|------|--------|------|------|------|
| period | 20 | 5 ~ 100 | 1 | 中轨 MA 周期 |
| multiplier | 2.0 | 1.0 ~ 4.0 | 0.1 | 标准差倍数 |

### 7.4 ATR

| 参数 | 默认值 | 范围 | 步长 | 说明 |
|------|--------|------|------|------|
| period | 14 | 2 ~ 50 | 1 | ATR 平滑周期 |

---

## 8. 文件结构

```
task02_indicator_lab/
├── indicator-lab-spec.md              # 技术指标计算规范 (已有)
├── indicator-tool-spec.md             # 本文件 — 工具产品设计文档
├── indicator_tool.html                # 主工具页面 (待开发)
├── 中芯国际_hk00981_近一年数据.csv    # 数据文件 (已有)
├── 中芯国际_sh688981_近一年数据.csv    # 数据文件 (已有)
├── 比亚迪_sz002594_近一年数据.csv      # 数据文件 (已有)
├── 比亚迪_hk01211_近一年数据.csv       # 数据文件 (已有)
└── 长江电力_sh600900_近一年数据.csv    # 数据文件 (已有)
```

---

## 9. 约束与假设

- CSV 文件与 HTML **同目录放置**，通过相对路径 `fetch()` 加载
- 所有 CSV 的列名一致: `date, open, close, high, low, volume, amount`
- 不同股票的交易日数量可能不同 (A股 ~242天, 港股 ~245天)
- 浏览器需支持 ES6 (Chrome/Edge/Firefox 近两年版本)
- 港股/美股/其他市场股票只需在 STOCK_REGISTRY 中添加条目即可扩展
