"""Generate 兆易创新A股技术指标实验室 notebook."""
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
        "version": "3.13.12"
    }
}

cells = []

def md(source):
    cells.append(nbf.v4.new_markdown_cell(source))

def code(source):
    cells.append(nbf.v4.new_code_cell(source))

# ============================================================
# Chapter 0: 环境 & 数据准备
# ============================================================
md("""# 兆易创新 A股 技术指标实验室

> **股票**: 兆易创新 (GigaDevice) | **代码**: 603986.SH  
> **数据源**: akshare (Sina 源) | **复权**: 前复权 (qfq)  
> **覆盖范围**: 约 2025-07 ~ 2026-07 (约 242 个交易日)

---

## Chapter 0: 环境 & 数据准备""")

code("""import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

print("✓ 环境准备完成")
print(f"  NumPy:  {np.__version__}")
print(f"  Pandas: {pd.__version__}")
print(f"  Plotly: {go.__version__ if hasattr(go, '__version__') else 'loaded'}")""")

code("""# 加载数据
df = pd.read_csv('./兆易创新_603986_近一年数据.csv')
df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
df = df.sort_values('trade_date').reset_index(drop=True)

# A股 volume 单位转换: 股 → 手 (÷100)
df['vol_shou'] = df['vol'] / 100

print(f"数据行数: {len(df)}")
print(f"日期范围: {df['trade_date'].min().strftime('%Y-%m-%d')} ~ {df['trade_date'].max().strftime('%Y-%m-%d')}")
print(f"交易日数: {len(df)} 天\\n")
print("前 5 行数据预览:")
display(df[['trade_date', 'open', 'high', 'low', 'close', 'vol_shou', 'amount']].head())
print("\\n后 5 行数据预览:")
display(df[['trade_date', 'open', 'high', 'low', 'close', 'vol_shou', 'amount']].tail())
print("\\n基本统计:")
display(df[['open', 'high', 'low', 'close', 'amount']].describe().round(2))""")

code("""# K线概览图
fig = go.Figure(data=[
    go.Candlestick(
        x=df['trade_date'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name='K线',
        increasing_line_color='#e83939',
        decreasing_line_color='#2ba350'
    )
])

fig.update_layout(
    title='兆易创新 (603986.SH) 近一年 K 线概览',
    xaxis_title='日期',
    yaxis_title='价格 (元)',
    template='plotly_white',
    height=500,
    hovermode='x unified'
)
fig.show()""")

# ============================================================
# Chapter 1: RSI
# ============================================================
md("""---

## Chapter 1: RSI (相对强弱指数)

### 计算原理

$$\\Delta price[i] = close[i] - close[i-1]$$

$$gain[i] = \\max(\\Delta price[i], 0)$$

$$loss[i] = \\max(-\\Delta price[i], 0)$$

$$avg\\_gain = SMA(gain, 14)$$

$$avg\\_loss = SMA(loss, 14)$$

$$RS = \\frac{avg\\_gain}{avg\\_loss}$$

$$RSI = 100 - \\frac{100}{1 + RS}$$

**解读规则**: RSI > 70 为超买区域，RSI < 30 为超卖区域。""")

code("""print("=" * 60)
print("Chapter 1: RSI(14) 计算")
print("=" * 60)

# 1.1 日收益率
delta = df['close'].diff()
print(f"\\n1.1 日收益率 (Δprice):")
print(f"  序列长度: {len(delta)}，前 5 个值:")
print(delta.head(10).to_string())

# 1.2 分离涨幅与跌幅
gain = delta.clip(lower=0)
loss = (-delta).clip(lower=0)
print(f"\\n1.2 涨幅 (gain) 前 10 个值:")
print(gain.head(10).to_string())
print(f"\\n   跌幅 (loss) 前 10 个值:")
print(loss.head(10).to_string())""")

code("""# 1.3 14日平均涨幅/跌幅 (SMA平滑)
avg_gain = gain.rolling(window=14).mean()
avg_loss = loss.rolling(window=14).mean()

print(f"\\n1.3 14日平均涨幅 (avg_gain) 从第14天开始:")
print(avg_gain.iloc[13:18].to_string())
print(f"\\n   14日平均跌幅 (avg_loss) 从第14天开始:")
print(avg_loss.iloc[13:18].to_string())""")

code("""# 1.4 RS → RSI
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

print(f"\\n1.4-1.5 RSI 序列 (前 15 个有效值):")
print(df[['trade_date', 'close', 'rsi']].dropna(subset=['rsi']).head(15).to_string(index=False))
print(f"\\nRSI 有效值数量: {df['rsi'].notna().sum()} (期望 = {len(df)} - 14 = {len(df)-14})")
print(f"RSI 最新值: {df['rsi'].iloc[-1]:.2f}")
print(f"RSI 最大值: {df['rsi'].max():.2f}")
print(f"RSI 最小值: {df['rsi'].min():.2f}")""")

code("""# 1.6 RSI 可视化
fig_rsi = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.08,
    row_heights=[0.6, 0.4],
    subplot_titles=('兆易创新 收盘价', 'RSI(14)')
)

# 收盘价
fig_rsi.add_trace(go.Scatter(
    x=df['trade_date'], y=df['close'],
    mode='lines', name='Close',
    line=dict(color='#333333', width=1.5)
), row=1, col=1)

# RSI
fig_rsi.add_trace(go.Scatter(
    x=df['trade_date'], y=df['rsi'],
    mode='lines', name='RSI(14)',
    line=dict(color='#378add', width=1.5)
), row=2, col=1)

# 参考线
fig_rsi.add_hline(y=70, line=dict(color='#e83939', dash='dash', width=1), row=2, col=1)
fig_rsi.add_hline(y=30, line=dict(color='#2ba350', dash='dash', width=1), row=2, col=1)
fig_rsi.add_hline(y=50, line=dict(color='#999999', dash='dot', width=0.8), row=2, col=1)

# 超买/超卖区域着色
fig_rsi.add_hrect(y0=70, y1=100, fillcolor='#e83939', opacity=0.05, line_width=0, row=2, col=1)
fig_rsi.add_hrect(y0=0, y1=30, fillcolor='#2ba350', opacity=0.05, line_width=0, row=2, col=1)

fig_rsi.update_layout(
    template='plotly_white',
    height=600,
    hovermode='x unified',
    showlegend=False
)
fig_rsi.update_yaxes(title_text='价格 (元)', row=1, col=1)
fig_rsi.update_yaxes(title_text='RSI', range=[0, 100], row=2, col=1)
fig_rsi.show()
print("\\n✓ RSI 图表: 蓝色线=RSI(14), 红色虚线=70(超买), 绿色虚线=30(超卖)")""")

# ============================================================
# Chapter 2: MACD
# ============================================================
md("""---

## Chapter 2: MACD (指数平滑异同移动平均线)

### 计算原理

$$EMA_t(N) = close_t \\times \\frac{2}{N+1} + EMA_{t-1}(N) \\times (1 - \\frac{2}{N+1})$$

$$DIF = EMA(close, 12) - EMA(close, 26)$$

$$DEA = EMA(DIF, 9)$$

$$MACD\\_BAR = 2 \\times (DIF - DEA)$$

**金叉 (买入信号)**: DIF 从下方上穿 DEA  
**死叉 (卖出信号)**: DIF 从上方下穿 DEA""")

code("""print("=" * 60)
print("Chapter 2: MACD(12, 26, 9) 计算")
print("=" * 60)

# 2.1 EMA 函数实现
def ema(series, n):
    result = pd.Series(np.nan, index=series.index)
    # 剔除 NaN, 从第一个有效值开始计算
    clean = series.dropna()
    if len(clean) < n:
        return result
    # 初始值用前 n 个有效值的 SMA
    start_idx = clean.index[n - 1]
    start_loc = series.index.get_loc(start_idx)
    result.iloc[start_loc] = clean.iloc[:n].mean()
    multiplier = 2 / (n + 1)
    for i in range(start_loc + 1, len(series)):
        if pd.notna(series.iloc[i]):
            result.iloc[i] = series.iloc[i] * multiplier + result.iloc[i - 1] * (1 - multiplier)
        else:
            result.iloc[i] = result.iloc[i - 1]  # 缺失值沿用前值
    return result

# 验证 EMA 函数
test_series = pd.Series([22, 22.5, 23, 22.8, 23.2, 23.1, 22.9, 23.5])
test_ema5 = ema(test_series, 5)
print("2.1 EMA 函数验证 (N=5):")
print(f"  输入序列: {test_series.tolist()}")
print(f"  EMA(5):    {test_ema5.round(4).tolist()}")
print(f"  初始值 (SMA): {test_series.iloc[:5].mean():.4f}")
print(f"  第5天 EMA: {test_ema5.iloc[4]:.4f} (应等于 SMA)")
print(f"  第6天 EMA: {test_ema5.iloc[5]:.4f} = 23.1×0.333 + {test_ema5.iloc[4]:.4f}×0.667")""")

code("""# 2.2 EMA(12) 与 EMA(26)
ema12 = ema(df['close'], 12)
ema26 = ema(df['close'], 26)
df['ema12'] = ema12
df['ema26'] = ema26

print(f"\\n2.2 EMA(12) 从第12天开始有效:")
print(ema12.dropna().head(5).to_string())
print(f"\\n   EMA(26) 从第26天开始有效:")
print(ema26.dropna().head(5).to_string())""")

code("""# 2.3 DIF = EMA(12) - EMA(26)
df['dif'] = ema12 - ema26
print(f"\\n2.3 DIF 序列 (前5个有效值):")
print(df[['trade_date', 'close', 'ema12', 'ema26', 'dif']].dropna(subset=['dif']).head(5).to_string(index=False))""")

code("""# 2.4 DEA = EMA(DIF, 9)
dif_series = df['dif'].copy()
dea = ema(dif_series, 9)
df['dea'] = dea
print(f"\\n2.4 DEA 序列 (前5个有效值):")
valid_dea = df.dropna(subset=['dea'])
print(valid_dea[['trade_date', 'dif', 'dea']].head(5).to_string(index=False))""")

code("""# 2.5 MACD 柱 = 2 × (DIF - DEA)
df['macd_bar'] = 2 * (df['dif'] - df['dea'])

# 2.6 金叉/死叉信号
df['cross_signal'] = 0
prev_dif = df['dif'].shift(1)
prev_dea = df['dea'].shift(1)
# 金叉: 前一天 DIF <= DEA 且当天 DIF > DEA
golden = (df['dif'] > df['dea']) & (prev_dif <= prev_dea)
# 死叉: 前一天 DIF >= DEA 且当天 DIF < DEA
dead = (df['dif'] < df['dea']) & (prev_dif >= prev_dea)
df.loc[golden, 'cross_signal'] = 1
df.loc[dead, 'cross_signal'] = -1

golden_dates = df[df['cross_signal'] == 1]
dead_dates = df[df['cross_signal'] == -1]

print(f"\\n2.5-2.6 MACD 计算结果:")
print(f"  DIF 最新值:  {df['dif'].iloc[-1]:.2f}")
print(f"  DEA 最新值:  {df['dea'].iloc[-1]:.2f}")
print(f"  BAR 最新值:  {df['macd_bar'].iloc[-1]:.2f}")
print(f"  金叉次数: {len(golden_dates)}")
print(f"  死叉次数: {len(dead_dates)}")
if len(golden_dates) > 0:
    print(f"  最近金叉: {golden_dates['trade_date'].iloc[-1].strftime('%Y-%m-%d')}")
if len(dead_dates) > 0:
    print(f"  最近死叉: {dead_dates['trade_date'].iloc[-1].strftime('%Y-%m-%d')}")""")

code("""# 2.7 MACD 可视化
fig_macd = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.55, 0.45],
    subplot_titles=('兆易创新 收盘价 & EMA', 'MACD(12,26,9)')
)

# 收盘价 + EMA
fig_macd.add_trace(go.Scatter(
    x=df['trade_date'], y=df['close'],
    mode='lines', name='Close',
    line=dict(color='#333333', width=1.2)
), row=1, col=1)
fig_macd.add_trace(go.Scatter(
    x=df['trade_date'], y=df['ema12'],
    mode='lines', name='EMA(12)',
    line=dict(color='#e83939', width=1)
), row=1, col=1)
fig_macd.add_trace(go.Scatter(
    x=df['trade_date'], y=df['ema26'],
    mode='lines', name='EMA(26)',
    line=dict(color='#378add', width=1)
), row=1, col=1)

# MACD 柱 + DIF + DEA
colors = ['#e83939' if v >= 0 else '#2ba350' for v in df['macd_bar']]
fig_macd.add_trace(go.Bar(
    x=df['trade_date'], y=df['macd_bar'],
    name='BAR', marker_color=colors,
    opacity=0.7
), row=2, col=1)
fig_macd.add_trace(go.Scatter(
    x=df['trade_date'], y=df['dif'],
    mode='lines', name='DIF',
    line=dict(color='#e83939', width=1.2)
), row=2, col=1)
fig_macd.add_trace(go.Scatter(
    x=df['trade_date'], y=df['dea'],
    mode='lines', name='DEA',
    line=dict(color='#378add', width=1.2)
), row=2, col=1)

# 金叉/死叉标记
if len(golden_dates) > 0:
    fig_macd.add_trace(go.Scatter(
        x=golden_dates['trade_date'], y=golden_dates['dif'],
        mode='markers', name='金叉',
        marker=dict(symbol='triangle-up', size=10, color='#e83939')
    ), row=2, col=1)
if len(dead_dates) > 0:
    fig_macd.add_trace(go.Scatter(
        x=dead_dates['trade_date'], y=dead_dates['dif'],
        mode='markers', name='死叉',
        marker=dict(symbol='triangle-down', size=10, color='#2ba350')
    ), row=2, col=1)

fig_macd.add_hline(y=0, line=dict(color='#999999', dash='dot', width=0.8), row=2, col=1)

fig_macd.update_layout(
    template='plotly_white',
    height=650,
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5)
)
fig_macd.update_yaxes(title_text='价格 (元)', row=1, col=1)
fig_macd.update_yaxes(title_text='MACD', row=2, col=1)
fig_macd.show()
print("\\n✓ MACD 图表: 上图为收盘价+EMA双线, 下图为DIF/DEA/BAR + 金叉死叉标记")""")

# ============================================================
# Chapter 3: Bollinger Bands
# ============================================================
md("""---

## Chapter 3: 布林带 (Bollinger Bands)

### 计算原理

$$MA(20) = SMA(close, 20)$$

$$\\sigma(20) = std(close, 20,\\ ddof=1)$$

$$上轨 = MA + 2\\sigma$$

$$下轨 = MA - 2\\sigma$$

$$带宽 = \\frac{上轨 - 下轨}{MA}$$

$$\\%B = \\frac{close - 下轨}{上轨 - 下轨}$$

**解读规则**: %B > 1 表示价格突破上轨 (超强), %B < 0 表示价格跌破下轨 (超弱)。""")

code("""print("=" * 60)
print("Chapter 3: Bollinger Bands(20, ±2σ) 计算")
print("=" * 60)

# 3.1 中轨 MA(20)
df['bb_ma'] = df['close'].rolling(window=20).mean()
print(f"\\n3.1 中轨 MA(20) 从第20天开始有效:")
print(df[['trade_date', 'close', 'bb_ma']].dropna(subset=['bb_ma']).head(5).to_string(index=False))""")

code("""# 3.2 滚动标准差 σ(20)
df['bb_std'] = df['close'].rolling(window=20).std(ddof=1)  # 样本标准差
print(f"\\n3.2 滚动标准差 σ(20):")
print(df[['trade_date', 'close', 'bb_ma', 'bb_std']].dropna(subset=['bb_std']).head(5).to_string(index=False))""")

code("""# 3.3 上轨 / 下轨
df['bb_upper'] = df['bb_ma'] + 2 * df['bb_std']
df['bb_lower'] = df['bb_ma'] - 2 * df['bb_std']

# 3.4 带宽 / %B
df['bb_bw'] = (df['bb_upper'] - df['bb_lower']) / df['bb_ma']
df['bb_pctb'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

print(f"\\n3.3-3.4 布林带完整结果 (最新 10 天):")
cols = ['trade_date', 'close', 'bb_ma', 'bb_upper', 'bb_lower', 'bb_bw', 'bb_pctb']
bb_valid = df[cols].dropna(subset=['bb_upper'])
display(bb_valid.tail(10).round(2))

print(f"\\n布林带统计:")
print(f"  最新中轨: {df['bb_ma'].iloc[-1]:.2f}")
print(f"  最新上轨: {df['bb_upper'].iloc[-1]:.2f}")
print(f"  最新下轨: {df['bb_lower'].iloc[-1]:.2f}")
print(f"  最新带宽: {df['bb_bw'].iloc[-1]:.4f} ({df['bb_bw'].iloc[-1]*100:.2f}%)")
print(f"  最新 %B:  {df['bb_pctb'].iloc[-1]:.4f}")
print(f"  有效值:   {df['bb_ma'].notna().sum()} (期望 = {len(df)} - 19 = {len(df)-19})")""")

code("""# 3.5 布林带可视化
fig_bb = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.08,
    row_heights=[0.6, 0.4],
    subplot_titles=('兆易创新 布林带(20,±2σ)', '带宽 (Bandwidth)')
)

# K线 + 布林带
fig_bb.add_trace(go.Candlestick(
    x=df['trade_date'], open=df['open'], high=df['high'],
    low=df['low'], close=df['close'],
    name='K线',
    increasing_line_color='#e83939', decreasing_line_color='#2ba350',
    showlegend=False
), row=1, col=1)

for name, col, color in [('中轨 MA(20)', 'bb_ma', '#378add'),
                          ('上轨 BB+2σ', 'bb_upper', '#e83939'),
                          ('下轨 BB-2σ', 'bb_lower', '#2ba350')]:
    fig_bb.add_trace(go.Scatter(
        x=df['trade_date'], y=df[col],
        mode='lines', name=name,
        line=dict(color=color, width=1.2, dash='dash' if 'upper' in name or 'lower' in name else 'solid')
    ), row=1, col=1)

# 上/下轨之间填充
fig_bb.add_trace(go.Scatter(
    x=df['trade_date'], y=df['bb_upper'],
    mode='lines', line=dict(width=0), showlegend=False
), row=1, col=1)
fig_bb.add_trace(go.Scatter(
    x=df['trade_date'], y=df['bb_lower'],
    mode='lines', fill='tonexty', fillcolor='rgba(55,138,221,0.08)',
    line=dict(width=0), showlegend=False
), row=1, col=1)

# 带宽
fig_bb.add_trace(go.Scatter(
    x=df['trade_date'], y=df['bb_bw'],
    mode='lines', name='带宽',
    line=dict(color='#378add', width=1.5),
    fill='tozeroy', fillcolor='rgba(55,138,221,0.1)'
), row=2, col=1)

fig_bb.update_layout(
    template='plotly_white',
    height=650,
    hovermode='x unified'
)
fig_bb.update_yaxes(title_text='价格 (元)', row=1, col=1)
fig_bb.update_yaxes(title_text='带宽比率', row=2, col=1)
fig_bb.show()
print("\\n✓ 布林带图表: 上图K线+三轨, 下图带宽变化")""")

# ============================================================
# Chapter 4: ATR
# ============================================================
md("""---

## Chapter 4: ATR (平均真实波幅)

### 计算原理

$$TR[i] = \\max\\left(
    \\begin{aligned}
    &high[i] - low[i] \\\\
    &|high[i] - close[i-1]| \\\\
    &|low[i] - close[i-1]|
    \\end{aligned}
\\right)$$

$$ATR = EMA(TR, 14)$$

**解读规则**: ATR 衡量市场波动率，数值越大表示波动越剧烈。常用于止损设置 (如 2×ATR 止损) 和仓位规模计算。""")

code("""print("=" * 60)
print("Chapter 4: ATR(14) 计算")
print("=" * 60)

# 4.1-4.2 True Range 计算
prev_close = df['close'].shift(1)
tr1 = df['high'] - df['low']                        # 当日振幅
tr2 = (df['high'] - prev_close).abs()               # 最高 - 昨收
tr3 = (df['low'] - prev_close).abs()                # 最低 - 昨收
df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

print(f"\\n4.1-4.2 True Range 计算验证 (前8天):")
print(f"{'日期':>12s} {'High':>8s} {'Low':>8s} {'PrevClose':>10s} {'TR1':>8s} {'TR2':>8s} {'TR3':>8s} {'TR':>8s}")
print("-" * 72)
for i in range(min(8, len(df))):
    d = df.iloc[i]
    p = df.iloc[i-1] if i > 0 else None
    pc = p['close'] if p is not None else float('nan')
    t1 = d['high'] - d['low']
    t2 = abs(d['high'] - pc) if p is not None else float('nan')
    t3 = abs(d['low'] - pc) if p is not None else float('nan')
    print(f"{d['trade_date'].strftime('%Y-%m-%d'):>12s} {d['high']:>8.2f} {d['low']:>8.2f} "
          f"{pc:>10.2f} {t1:>8.2f} {t2:>8.2f} {t3:>8.2f} {d['tr']:>8.2f}")""")

code("""# 4.3 14日 ATR (EMA平滑)
tr_series = df['tr'].copy()
atr = ema(tr_series, 14)
df['atr'] = atr

print(f"\\n4.3 ATR(14) 序列 (前10个有效值):")
atr_valid = df.dropna(subset=['atr'])
print(atr_valid[['trade_date', 'close', 'tr', 'atr']].head(10).to_string(index=False))

print(f"\\nATR 统计:")
print(f"  ATR 最新值:  {df['atr'].iloc[-1]:.2f}")
print(f"  ATR 最大值:  {df['atr'].max():.2f}")
print(f"  ATR 最小值:  {df['atr'].min():.2f}")
print(f"  ATR 均值:    {df['atr'].mean():.2f}")
print(f"  ATR/Close:   {df['atr'].iloc[-1] / df['close'].iloc[-1] * 100:.2f}% (波动率占比)")
print(f"  有效值数量:  {df['atr'].notna().sum()} (期望 = {len(df)} - 13 = {len(df)-13})")""")

code("""# 4.4 ATR 可视化
fig_atr = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.08,
    row_heights=[0.55, 0.45],
    subplot_titles=('兆易创新 K线', 'ATR(14) - 平均真实波幅')
)

# K线
fig_atr.add_trace(go.Candlestick(
    x=df['trade_date'], open=df['open'], high=df['high'],
    low=df['low'], close=df['close'],
    name='K线',
    increasing_line_color='#e83939', decreasing_line_color='#2ba350',
    showlegend=False
), row=1, col=1)

# ATR
fig_atr.add_trace(go.Scatter(
    x=df['trade_date'], y=df['atr'],
    mode='lines', name='ATR(14)',
    line=dict(color='#e83939', width=1.8),
    fill='tozeroy', fillcolor='rgba(232,57,57,0.08)'
), row=2, col=1)

# ATR 均值线
atr_mean = df['atr'].mean()
fig_atr.add_hline(y=atr_mean, line=dict(color='#378add', dash='dash', width=1),
                   annotation_text=f'均值 {atr_mean:.2f}', row=2, col=1)

fig_atr.update_layout(
    template='plotly_white',
    height=600,
    hovermode='x unified'
)
fig_atr.update_yaxes(title_text='价格 (元)', row=1, col=1)
fig_atr.update_yaxes(title_text='ATR', row=2, col=1)
fig_atr.show()
print(f"\\n✓ ATR 图表: 上图为K线走势, 下图为ATR波动率, 蓝色虚线为ATR均值({atr_mean:.2f})")""")

# ============================================================
# Chapter 5: 综合总结
# ============================================================
md("""---

## Chapter 5: 综合总结""")

code("""print("=" * 60)
print("Chapter 5: 四个指标综合汇总")
print("=" * 60)

latest = df.iloc[-1]
print(f"\\n📊 兆易创新 (603986.SH) 最新交易日: {latest['trade_date'].strftime('%Y-%m-%d')}")
print(f"   收盘价: {latest['close']:.2f} 元")
print()

# 汇总表
summary = pd.DataFrame({
    '指标': ['RSI(14)', 'MACD DIF', 'MACD DEA', 'MACD BAR',
             'BB 中轨', 'BB 上轨', 'BB 下轨', 'BB 带宽', 'BB %B',
             'ATR(14)'],
    '最新值': [
        f"{latest['rsi']:.2f}",
        f"{latest['dif']:.2f}",
        f"{latest['dea']:.2f}",
        f"{latest['macd_bar']:.2f}",
        f"{latest['bb_ma']:.2f}",
        f"{latest['bb_upper']:.2f}",
        f"{latest['bb_lower']:.2f}",
        f"{latest['bb_bw']:.4f}",
        f"{latest['bb_pctb']:.4f}",
        f"{latest['atr']:.2f}"
    ],
    '信号': [
        '超买 (>70)' if latest['rsi'] > 70 else ('超卖 (<30)' if latest['rsi'] < 30 else '中性'),
        '多头 (DIF>0)' if latest['dif'] > 0 else '空头 (DIF<0)',
        '多头 (DEA>0)' if latest['dea'] > 0 else '空头 (DEA<0)',
        '红柱 (多头)' if latest['macd_bar'] > 0 else '绿柱 (空头)',
        '—',
        '—',
        '—',
        f"{'高波动' if latest['bb_bw'] > df['bb_bw'].quantile(0.75) else '正常'}",
        '突破上轨' if latest['bb_pctb'] > 1 else ('跌破下轨' if latest['bb_pctb'] < 0 else '带内运行'),
        f"{'高波动' if latest['atr'] > df['atr'].mean() else '低波动'}"
    ]
})

display(summary)

# 四指标综合面板
fig_summary = make_subplots(
    rows=5, cols=1, shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.3, 0.18, 0.18, 0.18, 0.16],
    subplot_titles=('兆易创新 收盘价', 'RSI(14)', 'MACD(12,26,9)', '布林带(20,±2σ)', 'ATR(14)')
)

# Row 1: 收盘价
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['close'],
    mode='lines', name='Close',
    line=dict(color='#333333', width=1.5)
), row=1, col=1)

# Row 2: RSI
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['rsi'],
    mode='lines', name='RSI',
    line=dict(color='#378add', width=1.2)
), row=2, col=1)
fig_summary.add_hline(y=70, line=dict(color='#e83939', dash='dash', width=0.8), row=2, col=1)
fig_summary.add_hline(y=30, line=dict(color='#2ba350', dash='dash', width=0.8), row=2, col=1)

# Row 3: MACD
colors_bar = ['#e83939' if v >= 0 else '#2ba350' for v in df['macd_bar']]
fig_summary.add_trace(go.Bar(
    x=df['trade_date'], y=df['macd_bar'],
    name='BAR', marker_color=colors_bar, opacity=0.6
), row=3, col=1)
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['dif'],
    mode='lines', name='DIF', line=dict(color='#e83939', width=1)
), row=3, col=1)
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['dea'],
    mode='lines', name='DEA', line=dict(color='#378add', width=1)
), row=3, col=1)
fig_summary.add_hline(y=0, line=dict(color='#999', dash='dot', width=0.5), row=3, col=1)

# Row 4: 布林带
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['bb_upper'],
    mode='lines', name='BB上轨', line=dict(color='#e83939', width=0.8, dash='dash')
), row=4, col=1)
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['bb_ma'],
    mode='lines', name='BB中轨', line=dict(color='#378add', width=1)
), row=4, col=1)
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['bb_lower'],
    mode='lines', name='BB下轨', line=dict(color='#2ba350', width=0.8, dash='dash')
), row=4, col=1)
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['close'],
    mode='lines', name='Close', line=dict(color='#333', width=1.2), showlegend=False
), row=4, col=1)

# Row 5: ATR
fig_summary.add_trace(go.Scatter(
    x=df['trade_date'], y=df['atr'],
    mode='lines', name='ATR',
    line=dict(color='#e83939', width=1.2),
    fill='tozeroy', fillcolor='rgba(232,57,57,0.06)'
), row=5, col=1)
fig_summary.add_hline(y=atr_mean, line=dict(color='#378add', dash='dash', width=0.8), row=5, col=1)

fig_summary.update_layout(
    template='plotly_white',
    height=1100,
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5)
)

for row, title in [(1, '价格 (元)'), (2, 'RSI'), (3, 'MACD'), (4, '价格 (元)'), (5, 'ATR')]:
    fig_summary.update_yaxes(title_text=title, row=row, col=1)

fig_summary.show()
print("\\n✓ 综合面板: 五子图面板, 从上到下依次为收盘价、RSI、MACD、布林带、ATR")""")

code("""# 保存指标计算结果到 CSV
out_cols = ['trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount',
            'rsi', 'ema12', 'ema26', 'dif', 'dea', 'macd_bar',
            'bb_ma', 'bb_std', 'bb_upper', 'bb_lower', 'bb_bw', 'bb_pctb',
            'tr', 'atr']
output_df = df[out_cols].copy()
output_df['trade_date'] = output_df['trade_date'].dt.strftime('%Y-%m-%d')
output_csv = './兆易创新_603986_技术指标汇总.csv'
output_df.round(4).to_csv(output_csv, index=False, encoding='utf-8-sig')
print(f"\\n✓ 指标计算结果已保存到: {output_csv}")
print(f"  总行数: {len(output_df)}")
print(f"  总列数: {len(output_df.columns)}")
print(f"\\n{'='*60}")
print("  兆易创新技术指标实验室 — 计算完成!")
print(f"{'='*60}")""")

# ============================================================
# Assemble notebook
# ============================================================
nb.cells = cells

# Save
output_path = './兆易创新A股技术指标实验室.ipynb'
with open(output_path, 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print(f"Notebook saved to: {output_path}")
print(f"Total cells: {len(cells)}")
