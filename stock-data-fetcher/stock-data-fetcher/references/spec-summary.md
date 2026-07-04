# stock-data-spec.md v2.0 核心要点

## L1 数据字段标准

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| date | string | - | YYYY-MM-DD |
| open | float | 元 | 开盘价（前复权） |
| close | float | 元 | 收盘价 |
| high | float | 元 | 最高价 |
| low | float | 元 | 最低价 |
| volume | int | 手(A)/股(HK) | 成交量 |
| amount | float | 元/HKD | 成交额 |

数据按 date 升序排列。

## 数据层级 (L1-L4)

- **L1** 基础行情: 日线 OHLCV
- **L2** 增强市场: L1 + 周/月线 + 资金流向 + 融资融券 + 沪深港通
- **L3** 基本面: 财务指标 + 估值 + 股东数据
- **L4** 事件特色: 分红 + 业绩预告 + 龙虎榜 + AH 溢价率

## 单位标准化对照表

| 场景 | akshare 原始 | 标准单位 | 转换 |
|------|-------------|----------|------|
| A股 volume | 股 | 手 | ÷ 100 |
| 港股 volume | 股 | 股 | 无需 |
| akshare amount | 元/港元 | 元/港元 | 无需 |
| Tushare amount | 千元 | 元 | × 1000 |

## 股票登记模板

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
tags: [半导体龙头, AH双重上市]
```

## 工具链文件清单

| 脚本 | 输入 | 输出 |
|------|------|------|
| fetch_data.py | akshare API | JSON + CSV |
| gen_panels.py | JSON | HTML 面板 |
| qc_check.py | JSON | qc_report.json |
