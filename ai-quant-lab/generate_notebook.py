"""
Generate 中芯国际港股技术指标实验室.ipynb
Uses nbformat to create a structured Jupyter notebook.
"""
import nbformat as nbf
nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3"
    },
    "language_info": {
        "name": "python",
        "version": "3.13.0"
    }
}

cells = []

def md(source):
    cells.append(nbf.v4.new_markdown_cell(source))

def code(source):
    cells.append(nbf.v4.new_code_cell(source))

# ================================================================
# Chapter 0: 环境 & 数据准备
# ================================================================

md("""# 中芯国际港股 (00981.HK) 技术指标实验室

> **任务**: 手动计算 RSI、MACD、布林带、ATR 四个经典技术指标\\
> **数据**: 2025-07-04 ~ 2026-07-03, 245 个交易日, 前复权 (qfq)\\
> **原则**: 不使用 pandas-ta / ta-lib 等黑盒库, 全程手算公式, 中间步骤透明展示""")

md("""## Chapter 0 — 环境与数据准备""")

code("""import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# 颜色常量 (中国市场: 红涨绿跌)
RED   = '#e83939'
GREEN = '#2ba350'
BLUE  = '#378add'

pd.set_option('display.max_rows', 10)
pd.set_option('display.precision', 2)
print("环境准备完成 ✓")""")

code("""# 加载中芯国际港股 L1 数据
data_path = Path('./中芯国际_hk00981_近一年数据.json')
with open(data_path, encoding='utf-8') as f:
    raw = json.load(f)

records = raw['data']
print(f"数据源: {raw['_meta']['source']}")
print(f"复权方式: {raw['_meta']['adjust']}")
print(f"获取时间: {raw['_meta']['fetch_time']}")
print(f"记录总数: {len(records)}")
print(f"日期范围: {records[0]['date']} ~ {records[-1]['date']}")
print(f"字段: {list(records[0].keys())}")""")

code("""# 转换为 DataFrame 便于操作
df = pd.DataFrame(records)
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date').sort_index()

# 基础统计
print(f"交易天数: {len(df)}")
print(f"收盘价范围: ${df['close'].min():.2f} ~ ${df['close'].max():.2f} HKD")
print(f"最新收盘价: ${df['close'].iloc[-1]:.2f} HKD")
print(f"累计涨跌幅: {(df['close'].iloc[-1]/df['close'].iloc[0]-1)*100:+.2f}%")
print(f"日均成交量: {df['volume'].mean()/1e6:.1f} 百万股")
print(f"日均成交额: {df['amount'].mean()/1e8:.1f} 亿港元")
print()
print("最近 10 个交易日:")
print(df[['open','high','low','close','volume']].tail(10).round(2))""")

code("""# 价格走势总览
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3],
    vertical_spacing=0.05,
    subplot_titles=['收盘价走势', '成交量']
)

fig.add_trace(go.Scatter(
    x=df.index, y=df['close'], mode='lines',
    line=dict(color=BLUE, width=2), name='收盘价 (HKD)'
), row=1, col=1)

colors = [RED if df['close'].iloc[i] >= df['open'].iloc[i] else GREEN for i in range(len(df))]
fig.add_trace(go.Bar(
    x=df.index, y=df['volume'], marker_color=colors,
    name='成交量 (股)', showlegend=False
), row=2, col=1)

fig.update_layout(
    height=500, template='plotly_white',
    title='中芯国际 (00981.HK) 近一年日线概览',
    hovermode='x unified'
)
fig.update_yaxes(title_text='价格 (HKD)', row=1, col=1)
fig.update_yaxes(title_text='成交量 (股)', row=2, col=1)
fig.show()""")

md("""## 关键数据速查

| 指标 | 值 |
|------|-----|
| 起始价 | HK$43.95 |
| 最高价 | HK$91.05 (2025-10-06) |
| 最新价 | 见上方 |
| 日波动率 | 约 2.3% |

接下来, 我们将用这些原始 OHLCV 数据, 逐步手算四个经典技术指标。""")

# ================================================================
# Chapter 1: RSI
# ================================================================

md("""---

## Chapter 1 — RSI (相对强弱指数)

### 核心思想
RSI 衡量最近一段时间内价格**上涨力量与下跌力量的比值**, 映射到 0-100 区间。

$$\\Delta_t = Close_t - Close_{t-1}$$

$$\\text{gain}_t = \\max(\\Delta_t, 0), \\quad \\text{loss}_t = \\max(-\\Delta_t, 0)$$

$$\\text{avg\\_gain} = \\text{SMA}(\\text{gain}, 14), \\quad \\text{avg\\_loss} = \\text{SMA}(\\text{loss}, 14)$$

$$RS = \\frac{\\text{avg\\_gain}}{\\text{avg\\_loss}}$$

$$RSI = 100 - \\frac{100}{1 + RS}$$

> 当 RS → ∞ (全是阳线), RSI → 100\\
> 当 RS → 0 (全是阴线), RSI → 0\\
> 当 RS = 1 (涨跌均衡), RSI = 50""")

code("""# Step 1.1: 日收益率计算
N = 14  # RSI 参数

df['delta'] = df['close'].diff()  # Δprice = close[t] - close[t-1]

# 展示前 15 天的价格变化
demo = df[['close','delta']].head(18).copy()
demo.index = demo.index.strftime('%Y-%m-%d')
print("前 17 个交易日的价格变化 (第一天 delta 为 NaN):")
print(demo.round(2))""")

code("""# Step 1.2: 分离涨幅与跌幅
df['gain'] = np.where(df['delta'] > 0, df['delta'], 0)
df['loss'] = np.where(df['delta'] < 0, -df['delta'], 0)

print("前 18 行的 gain / loss 分离:")
demo2 = df[['delta','gain','loss']].head(18).copy()
demo2.index = demo2.index.strftime('%Y-%m-%d')
print(demo2.round(2))
print(f"\\n这 17 天中: 涨 {int((df['gain'].iloc[1:18] > 0).sum())} 天, 跌 {int((df['loss'].iloc[1:18] > 0).sum())} 天")
print(f"总涨幅: {df['gain'].iloc[1:18].sum():.2f}, 总跌幅: {df['loss'].iloc[1:18].sum():.2f}")""")

code("""# Step 1.3: 14 日简单移动平均 (SMA)
df['avg_gain'] = df['gain'].rolling(window=N).mean()
df['avg_loss'] = df['loss'].rolling(window=N).mean()

# Step 1.4 & 1.5: RS → RSI
df['rs'] = df['avg_gain'] / df['avg_loss']
df['rsi'] = 100 - 100 / (1 + df['rs'])

# 展示第一个有效 RSI 值 (第 15 天)
idx_start = N  # rolling 后第一个有效位置
print(f"第一个有效 RSI 出现在 {df.index[N].strftime('%Y-%m-%d')} (第 {N+1} 个交易日)")
print(f"  avg_gain = {df['avg_gain'].iloc[N]:.2f}")
print(f"  avg_loss = {df['avg_loss'].iloc[N]:.2f}")
print(f"  RS = {df['rs'].iloc[N]:.4f}")
print(f"  RSI = {df['rsi'].iloc[N]:.2f}")
print()
print(f"RSI 最新值 ({df.index[-1].strftime('%Y-%m-%d')}): {df['rsi'].iloc[-1]:.2f}")
print(f"RSI 区间: [{df['rsi'].dropna().min():.2f}, {df['rsi'].dropna().max():.2f}]")""")

code("""# Step 1.6: RSI 可视化
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, row_heights=[0.55, 0.45],
    vertical_spacing=0.05,
    subplot_titles=['收盘价', f'RSI({N}) — 超买线 70, 超卖线 30']
)

fig.add_trace(go.Scatter(
    x=df.index, y=df['close'], mode='lines',
    line=dict(color=BLUE, width=1.5), name='Close'
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df.index, y=df['rsi'], mode='lines',
    line=dict(color=RED, width=1.5), name=f'RSI({N})'
), row=2, col=1)

fig.add_hline(y=70, line_dash='dash', line_color=RED, opacity=0.6,
              annotation_text='超买 70', row=2, col=1)
fig.add_hline(y=30, line_dash='dash', line_color=GREEN, opacity=0.6,
              annotation_text='超卖 30', row=2, col=1)
fig.add_hline(y=50, line_dash='dot', line_color='gray', opacity=0.3, row=2, col=1)

fig.update_layout(
    height=550, template='plotly_white', hovermode='x unified',
    title=f'中芯国际港股 RSI({N}) 指标'
)
fig.update_yaxes(title_text='HKD', row=1, col=1)
fig.update_yaxes(title_text='RSI', range=[0, 100], row=2, col=1)
fig.show()""")

md("""### RSI 小结

- RSI > 70 → 超买区域, 价格可能回调
- RSI < 30 → 超卖区域, 价格可能反弹
- RSI = 50 → 多空均衡
- 中芯国际近一年 RSI 在 30~70 间正常摆动, 偶有触及极端区域""")

# ================================================================
# Chapter 2: MACD
# ================================================================

md("""---

## Chapter 2 — MACD (指数平滑异同移动平均线)

### 核心思想
MACD 通过**快慢两条 EMA 的差值**来衡量趋势强度与方向, 再用 DIF 的 EMA 作为信号线, 两者交叉产生交易信号。

$$\\text{EMA}_t(N) = Close_t \\times \\alpha + \\text{EMA}_{t-1}(N) \\times (1-\\alpha), \\quad \\alpha = \\frac{2}{N+1}$$

$$\\text{DIF} = \\text{EMA}(12) - \\text{EMA}(26)$$

$$\\text{DEA} = \\text{EMA}(\\text{DIF}, 9)$$

$$\\text{柱状体 (BAR)} = 2 \\times (\\text{DIF} - \\text{DEA})$$

**金叉**: DIF 从下方上穿 DEA → 做多信号\\
**死叉**: DIF 从上方下穿 DEA → 做空信号""")

code("""# Step 2.1: EMA 函数实现
def ema(series, span):
    \"\"\"计算指数加权移动平均 (EMA)\"\"\"
    return series.ewm(span=span, adjust=False).mean()

# Step 2.2: EMA(12) 快线, EMA(26) 慢线
df['ema12'] = ema(df['close'], 12)
df['ema26'] = ema(df['close'], 26)

# Step 2.3: DIF = 快 - 慢
df['dif'] = df['ema12'] - df['ema26']

# Step 2.4: DEA = EMA(DIF, 9)
df['dea'] = ema(df['dif'], 9)

# Step 2.5: 柱状体 (BAR) = 2 × (DIF - DEA)
df['macd_bar'] = 2 * (df['dif'] - df['dea'])

# 展示 MACD 三个组成部分的初值
day_33 = 33  # 等 EMA 充分收敛后查看
print(f"第 {day_33} 个交易日 ({df.index[day_33].strftime('%Y-%m-%d')}) MACD 初值:")
print(f"  EMA(12)  = {df['ema12'].iloc[day_33]:.2f}")
print(f"  EMA(26)  = {df['ema26'].iloc[day_33]:.2f}")
print(f"  DIF      = {df['dif'].iloc[day_33]:.2f}")
print(f"  DEA      = {df['dea'].iloc[day_33]:.2f}")
print(f"  BAR      = {df['macd_bar'].iloc[day_33]:.2f}")
print(f"\\n最新 ({df.index[-1].strftime('%Y-%m-%d')}):")
print(f"  DIF = {df['dif'].iloc[-1]:.2f}, DEA = {df['dea'].iloc[-1]:.2f}, BAR = {df['macd_bar'].iloc[-1]:.2f}")""")

code("""# Step 2.6: 金叉 / 死叉信号识别
# 金叉: 前一天 DIF <= DEA, 当天 DIF > DEA
df['signal'] = '—'
golden = (df['dif'].shift(1) <= df['dea'].shift(1)) & (df['dif'] > df['dea'])
dead   = (df['dif'].shift(1) >= df['dea'].shift(1)) & (df['dif'] < df['dea'])
df.loc[golden, 'signal'] = '金叉'
df.loc[dead, 'signal'] = '死叉'

golden_dates = df[df['signal'] == '金叉'].index
dead_dates   = df[df['signal'] == '死叉'].index

print(f"近一年出现 {len(golden_dates)} 次金叉, {len(dead_dates)} 次死叉")
print("\\n金叉日期:")
for d in golden_dates:
    print(f"  {d.strftime('%Y-%m-%d')}  DIF={df.loc[d,'dif']:.2f}  DEA={df.loc[d,'dea']:.2f}")
print("\\n死叉日期:")
for d in dead_dates:
    print(f"  {d.strftime('%Y-%m-%d')}  DIF={df.loc[d,'dif']:.2f}  DEA={df.loc[d,'dea']:.2f}")""")

code("""# Step 2.7: MACD 可视化
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5],
    vertical_spacing=0.05,
    subplot_titles=['收盘价 + EMA(12/26)', 'MACD(12,26,9) — DIF / DEA / BAR']
)

# 价格 + EMA
fig.add_trace(go.Scatter(
    x=df.index, y=df['close'], mode='lines',
    line=dict(color='#888', width=1), name='Close'
), row=1, col=1)
fig.add_trace(go.Scatter(
    x=df.index, y=df['ema12'], mode='lines',
    line=dict(color=RED, width=1.5), name='EMA(12)'
), row=1, col=1)
fig.add_trace(go.Scatter(
    x=df.index, y=df['ema26'], mode='lines',
    line=dict(color=GREEN, width=1.5), name='EMA(26)'
), row=1, col=1)

# MACD 子图
fig.add_trace(go.Scatter(
    x=df.index, y=df['dif'], mode='lines',
    line=dict(color=RED, width=1.5), name='DIF'
), row=2, col=1)
fig.add_trace(go.Scatter(
    x=df.index, y=df['dea'], mode='lines',
    line=dict(color=BLUE, width=1.5), name='DEA'
), row=2, col=1)

# 柱状体
bar_colors = [RED if v >= 0 else GREEN for v in df['macd_bar'].fillna(0)]
fig.add_trace(go.Bar(
    x=df.index, y=df['macd_bar'], marker_color=bar_colors,
    name='BAR', showlegend=True
), row=2, col=1)

# 金叉/死叉标注
fig.add_trace(go.Scatter(
    x=golden_dates, y=df.loc[golden_dates, 'dif'],
    mode='markers', marker=dict(symbol='triangle-up', size=12, color=RED),
    name='金叉 (买入)'
), row=2, col=1)
fig.add_trace(go.Scatter(
    x=dead_dates, y=df.loc[dead_dates, 'dif'],
    mode='markers', marker=dict(symbol='triangle-down', size=12, color=GREEN),
    name='死叉 (卖出)'
), row=2, col=1)

fig.add_hline(y=0, line_dash='dot', line_color='gray', opacity=0.3, row=2, col=1)

fig.update_layout(
    height=650, template='plotly_white', hovermode='x unified',
    title='中芯国际港股 MACD(12,26,9) 指标'
)
fig.show()""")

md("""### MACD 小结

- DIF 在零轴上方 → 多头市场; DIF 在零轴下方 → 空头市场
- 金叉: DIF 上穿 DEA, 柱状体由绿转红 → 趋势向上
- 死叉: DIF 下穿 DEA, 柱状体由红转绿 → 趋势向下
- 柱状体高度 = 多空力量强度""")

# ================================================================
# Chapter 3: Bollinger Bands
# ================================================================

md("""---

## Chapter 3 — Bollinger Bands (布林带)

### 核心思想
布林带基于统计学原理, 假设价格在均线附近服从正态分布, 使用 **均线 ± 2 个标准差** 构建通道, 约 95% 的价格落在带内。

$$\\text{中轨} = \\text{SMA}(Close, 20)$$

$$\\sigma_t = \\sqrt{\\frac{\\sum_{i=t-19}^{t} (Close_i - \\text{SMA}_t)^2}{19}}$$

$$\\text{上轨} = \\text{中轨} + 2\\sigma$$

$$\\text{下轨} = \\text{中轨} - 2\\sigma$$

$$\\text{带宽} = \\frac{\\text{上轨} - \\text{下轨}}{\\text{中轨}}$$

$$\\%B = \\frac{Close - \\text{下轨}}{\\text{上轨} - \\text{下轨}}$$""")

code("""# Step 3.1: 20 日移动平均 (中轨)
PERIOD = 20
df['bb_mid'] = df['close'].rolling(window=PERIOD).mean()

# Step 3.2: 20 日滚动标准差
df['bb_std'] = df['close'].rolling(window=PERIOD).std(ddof=1)  # 样本标准差

# Step 3.3: 上轨 / 下轨
MULT = 2.0  # 标准差倍数
df['bb_upper'] = df['bb_mid'] + MULT * df['bb_std']
df['bb_lower'] = df['bb_mid'] - MULT * df['bb_std']

# Step 3.4: 衍生指标
df['bb_width']   = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']  # 相对带宽
df['bb_pct_b']   = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])  # %B

# 展示
idx = PERIOD - 1  # 第一个有效值位置
print(f"第一个有效布林带出现在 {df.index[idx].strftime('%Y-%m-%d')} (第 {PERIOD} 个交易日)")
print(f"  中轨 (MA20)    = {df['bb_mid'].iloc[idx]:.2f}")
print(f"  标准差 σ       = {df['bb_std'].iloc[idx]:.2f}")
print(f"  上轨            = {df['bb_upper'].iloc[idx]:.2f}")
print(f"  下轨            = {df['bb_lower'].iloc[idx]:.2f}")
print(f"  带宽            = {df['bb_width'].iloc[idx]:.4f} ({df['bb_width'].iloc[idx]*100:.2f}%)")
print(f"  %B              = {df['bb_pct_b'].iloc[idx]:.3f}")
print()
print(f"最新 ({df.index[-1].strftime('%Y-%m-%d')}):")
print(f"  中轨 = {df['bb_mid'].iloc[-1]:.2f}, 上轨 = {df['bb_upper'].iloc[-1]:.2f}, 下轨 = {df['bb_lower'].iloc[-1]:.2f}")
print(f"  %B = {df['bb_pct_b'].iloc[-1]:.3f} (0=触下轨, 1=触上轨)")

# 统计突破事件
break_up   = (df['close'] > df['bb_upper']).sum()
break_down = (df['close'] < df['bb_lower']).sum()
print(f"\\n突破统计: 向上突破上轨 {break_up} 次, 向下突破下轨 {break_down} 次")""")

code("""# Step 3.5: 布林带可视化
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
    vertical_spacing=0.05,
    subplot_titles=['布林带 — 价格通道', f'%B 指标 (0=下轨, 1=上轨)']
)

# 价格 + 三条轨道
fig.add_trace(go.Scatter(
    x=df.index, y=df['close'], mode='lines',
    line=dict(color='#333', width=1.5), name='Close'
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df.index, y=df['bb_upper'], mode='lines',
    line=dict(color=RED, width=1, dash='dash'), name='上轨 MA+2σ',
    fill=None
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df.index, y=df['bb_mid'], mode='lines',
    line=dict(color=BLUE, width=1.5), name='中轨 MA(20)'
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df.index, y=df['bb_lower'], mode='lines',
    line=dict(color=GREEN, width=1, dash='dash'), name='下轨 MA-2σ',
    fill='tonexty', fillcolor='rgba(135,206,250,0.08)'  # 通道填充
), row=1, col=1)

# %B 子图
pct_b_colors = [RED if v >= 1 else (GREEN if v <= 0 else BLUE) for v in df['bb_pct_b'].fillna(0.5)]
fig.add_trace(go.Scatter(
    x=df.index, y=df['bb_pct_b'], mode='markers+lines',
    marker=dict(size=3, color=pct_b_colors), line=dict(color=BLUE, width=0.5),
    name='%B'
), row=2, col=1)

fig.add_hline(y=1, line_dash='dash', line_color=RED, opacity=0.5,
              annotation_text='上轨', row=2, col=1)
fig.add_hline(y=0, line_dash='dash', line_color=GREEN, opacity=0.5,
              annotation_text='下轨', row=2, col=1)
fig.add_hline(y=0.5, line_dash='dot', line_color='gray', opacity=0.25, row=2, col=1)

fig.update_layout(
    height=650, template='plotly_white', hovermode='x unified',
    title='中芯国际港股 Bollinger Bands(20,2)'
)
fig.show()""")

md("""### 布林带小结

- 价格在中轨上方 → 偏多; 下方 → 偏空
- 突破上轨: 超买信号, 但也可能是突破加速
- 跌破下轨: 超卖信号, 但也可能是恐慌下跌
- 带宽收窄 → 可能出现大行情 (盘整后的突破)
- %B 辅助判断价格在带内的相对位置""")

# ================================================================
# Chapter 4: ATR
# ================================================================

md("""---

## Chapter 4 — ATR (平均真实波幅)

### 核心思想
ATR 衡量价格的**平均波动幅度**, 不考虑方向。它用 True Range 来捕捉跳空缺口带来的真实波动。

$$\\text{TR}_t = \\max\\begin{cases}
High_t - Low_t \\\\
|High_t - Close_{t-1}| \\\\
|Low_t - Close_{t-1}|
\\end{cases}$$

$$\\text{ATR} = \\text{EMA}(\\text{TR}, 14)$$

> 关键: ATR **不提供**买卖方向, 它只告诉你"价格一天大概能动多少"。\\
> 实战用法: 止损 = 入场价 ± 2×ATR; 仓位 = 可承受亏损金额 / ATR""")

code("""# Step 4.1 & 4.2: True Range 计算
df['prev_close'] = df['close'].shift(1)

df['tr1'] = df['high'] - df['low']                           # 当日振幅
df['tr2'] = abs(df['high'] - df['prev_close'])               # 最高 - 昨收
df['tr3'] = abs(df['low'] - df['prev_close'])                # 昨收 - 最低

df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

# 展示三种距离和一个活生生的例子
example_idx = 34
print(f"第 {example_idx+1} 天 ({df.index[example_idx].strftime('%Y-%m-%d')}) True Range 计算示例:")
print(f"  Open={df['open'].iloc[example_idx]:.2f}  High={df['high'].iloc[example_idx]:.2f}  Low={df['low'].iloc[example_idx]:.2f}  Close={df['close'].iloc[example_idx]:.2f}")
print(f"  昨收 = {df['prev_close'].iloc[example_idx]:.2f}")
print(f"  TR1 (H-L)    = {df['tr1'].iloc[example_idx]:.2f}")
print(f"  TR2 |H-昨收|  = {df['tr2'].iloc[example_idx]:.2f}")
print(f"  TR3 |昨收-L|  = {df['tr3'].iloc[example_idx]:.2f}")
print(f"  → True Range = max(TR1, TR2, TR3) = {df['tr'].iloc[example_idx]:.2f}")""")

code("""# Step 4.3: 14 日 ATR (EMA 平滑)
N_ATR = 14
df['atr'] = df['tr'].ewm(span=N_ATR, adjust=False).mean()

# 展示
print(f"平均 True Range: {df['tr'].mean():.2f} HKD")
print(f"ATR(14) 最新值: {df['atr'].iloc[-1]:.2f} HKD")
print(f"ATR(14) 最小值: {df['atr'].min():.2f}  (波动最小时)")
print(f"ATR(14) 最大值: {df['atr'].max():.2f}  (波动最大时)")
print(f"ATR 占价格比例: {df['atr'].iloc[-1]/df['close'].iloc[-1]*100:.1f}%")

# 实战止损示例
entry_price = 78.0  # 假设入场价
stop_loss_1x = entry_price - df['atr'].iloc[-1]
stop_loss_2x = entry_price - 2 * df['atr'].iloc[-1]
print(f"\\n假设以 HK${entry_price:.2f} 入场:")
print(f"  1×ATR 止损位: HK${stop_loss_1x:.2f}")
print(f"  2×ATR 止损位: HK${stop_loss_2x:.2f}")""")

code("""# Step 4.4: ATR 可视化
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, row_heights=[0.55, 0.45],
    vertical_spacing=0.05,
    subplot_titles=['收盘价', 'ATR(14) 波动幅度']
)

fig.add_trace(go.Scatter(
    x=df.index, y=df['close'], mode='lines',
    line=dict(color=BLUE, width=1.5), name='Close'
), row=1, col=1)

fig.add_trace(go.Bar(
    x=df.index, y=df['tr'],
    marker_color='rgba(160,160,160,0.4)', name='True Range (日)',
    showlegend=True
), row=2, col=1)

fig.add_trace(go.Scatter(
    x=df.index, y=df['atr'], mode='lines',
    line=dict(color=RED, width=2), name='ATR(14) (平滑)'
), row=2, col=1)

fig.update_layout(
    height=550, template='plotly_white', hovermode='x unified',
    title='中芯国际港股 ATR(14) 波动率指标'
)
fig.update_yaxes(title_text='HKD', row=1, col=1)
fig.update_yaxes(title_text='HKD', row=2, col=1)
fig.show()""")

md("""### ATR 小结

- ATR 上升 → 市场波动加剧, 趋势可能启动或恐慌
- ATR 下降 → 市场趋于盘整, 可能酝酿突破
- ATR 本身不过滤方向 — 它只是告诉你"道路有多颠簸"
- 止损/仓位管理中 ATR 是不可或缺的工具""")

# ================================================================
# Chapter 5: 综合总结
# ================================================================

md("""---

## Chapter 5 — 综合总结""")

code("""# 四个指标最新值汇总
latest = df.iloc[-1]
prev = df.iloc[-2]

print("=" * 60)
print("中芯国际 (00981.HK) 技术指标综合报告")
print(f"日期: {df.index[-1].strftime('%Y-%m-%d')}  |  数据源: akshare (Sina)  |  复权: qfq")
print("=" * 60)
print(f"\\n收盘价: HK${latest['close']:.2f}")
print(f"前一日:  HK${prev['close']:.2f}")
print(f"单日涨跌: {(latest['close']-prev['close'])/prev['close']*100:+.2f}%")
print()

print(f"{'指标':<20} {'最新值':>12} {'信号/含义':>30}")
print("-" * 62)
rsi_signal = '超买 ▲' if latest['rsi'] > 70 else ('超卖 ▼' if latest['rsi'] < 30 else '中性 —')
print(f"{'RSI(14)':<20} {latest['rsi']:>12.2f} {rsi_signal:>30}")

macd_signal = '多头 ▲' if latest['dif'] > latest['dea'] else '空头 ▼'
bar_signal  = '红柱扩张' if latest['macd_bar'] > 0 else '绿柱收缩'
print(f"{'MACD DIF':<20} {latest['dif']:>12.2f} {macd_signal:>30}")
print(f"{'MACD DEA':<20} {latest['dea']:>12.2f}")
print(f"{'MACD BAR':<20} {latest['macd_bar']:>12.2f} {bar_signal:>30}")

bb_signal = '突破上轨 ▲' if latest['close'] > latest['bb_upper'] else ('跌破下轨 ▼' if latest['close'] < latest['bb_lower'] else '带内 —')
print(f"{'BB 中轨(20)':<20} {latest['bb_mid']:>12.2f}")
print(f"{'BB 上轨':<20} {latest['bb_upper']:>12.2f}")
print(f"{'BB 下轨':<20} {latest['bb_lower']:>12.2f} {bb_signal:>30}")
print(f"{'BB %B':<20} {latest['bb_pct_b']:>12.3f}")
print(f"{'BB 带宽':<20} {latest['bb_width']*100:>11.2f}%")

atr_signal = '高波动' if latest['atr'] > df['atr'].mean()*1.2 else ('低波动' if latest['atr'] < df['atr'].mean()*0.8 else '正常')
print(f"{'ATR(14)':<20} {latest['atr']:>12.2f} {atr_signal:>30}")
print(f"{'ATR/Price':<20} {latest['atr']/latest['close']*100:>11.2f}%")
print("-" * 62)""")

code("""# 四个指标整体走势并排图
fig = make_subplots(
    rows=4, cols=1, shared_xaxes=True,
    row_heights=[0.25, 0.25, 0.25, 0.25],
    vertical_spacing=0.03,
    subplot_titles=['RSI(14)', 'MACD(12,26,9)', 'Bollinger %B', 'ATR(14)']
)

# RSI
fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color=RED, width=1.2)), row=1, col=1)
fig.add_hline(y=70, line_dash='dash', line_color=RED, opacity=0.4, row=1, col=1)
fig.add_hline(y=30, line_dash='dash', line_color=GREEN, opacity=0.4, row=1, col=1)

# MACD
bar_colors = [RED if v >= 0 else GREEN for v in df['macd_bar'].fillna(0)]
fig.add_trace(go.Bar(x=df.index, y=df['macd_bar'], marker_color=bar_colors, showlegend=False), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['dif'], line=dict(color=RED, width=1)), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['dea'], line=dict(color=BLUE, width=1)), row=2, col=1)

# %B
fig.add_trace(go.Scatter(x=df.index, y=df['bb_pct_b'], line=dict(color=BLUE, width=1.2), fill='tozeroy', fillcolor='rgba(55,138,221,0.1)'), row=3, col=1)
fig.add_hline(y=1, line_dash='dash', line_color=RED, opacity=0.4, row=3, col=1)
fig.add_hline(y=0, line_dash='dash', line_color=GREEN, opacity=0.4, row=3, col=1)

# ATR
fig.add_trace(go.Scatter(x=df.index, y=df['atr'], line=dict(color=RED, width=1.5), fill='tozeroy', fillcolor='rgba(232,57,57,0.08)'), row=4, col=1)

fig.update_layout(
    height=900, template='plotly_white', hovermode='x unified',
    title='中芯国际 (00981.HK) 四大技术指标全景图'
)
fig.show()""")

md("""### 四个指标的关系与分工

| 维度 | RSI | MACD | 布林带 | ATR |
|------|-----|------|--------|-----|
| **核心问题** | 超买还是超卖？ | 趋势在加强还是衰竭？ | 价格在哪个合理区间？ | 一天能波动多少？ |
| **提供方向** | 间接 (极端值反转) | 是 (金叉/死叉) | 间接 (突破轨道) | 不提供 |
| **最佳场景** | 震荡市抄底逃顶 | 趋势跟踪 | 区间交易/突破确认 | 止损位/仓位管理 |
| **滞后性** | 中等 | 中等偏高 | 低 | 中等 |

### 使用建议

1. **趋势判断**: 先用 MACD 确认方向 (DIF 在零轴上方 + 金叉 = 做多)
2. **入场时机**: 用 RSI 找超卖区入场机会, 避免在超买区追高
3. **止损设定**: 用 ATR 设定科学止损 (如 2×ATR), 而非固定金额
4. **目标/风险**: 用布林带判断价格相对位置, 触及上轨时可考虑止盈

> **免责声明**: 本 Notebook 为教学目的展示技术指标的手算过程。技术指标基于历史数据, 不预测未来走势, 不构成任何投资建议。""")

# ================================================================
nb.cells = cells

import os
from pathlib import Path
output_dir = Path('C:/Users/Aaron Wu/Desktop/在线实习/task02_indicator_lab')
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / '中芯国际港股技术指标实验室.ipynb'

with open(output_path, 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print(f"Notebook written to: {output_path}")
print(f"Total cells: {len(nb.cells)}")
