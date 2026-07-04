"""从已抓取的数据生成独立 HTML 图表文件，双击浏览器即可查看。"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ── 数据加载 ──────────────────────────────────────────
df = pd.read_csv('./兆易创新_603986_近一年数据.csv')
df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
df = df.sort_values('trade_date').reset_index(drop=True)
df['vol_shou'] = df['vol'] / 100

# ── EMA 函数 ──────────────────────────────────────────
def ema(series, n):
    result = pd.Series(np.nan, index=series.index)
    clean = series.dropna()
    if len(clean) < n:
        return result
    start_idx = clean.index[n - 1]
    start_loc = series.index.get_loc(start_idx)
    result.iloc[start_loc] = clean.iloc[:n].mean()
    multiplier = 2 / (n + 1)
    for i in range(start_loc + 1, len(series)):
        if pd.notna(series.iloc[i]):
            result.iloc[i] = series.iloc[i] * multiplier + result.iloc[i - 1] * (1 - multiplier)
        else:
            result.iloc[i] = result.iloc[i - 1]
    return result

# ── RSI(14) ───────────────────────────────────────────
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = (-delta).clip(lower=0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
df['rsi'] = 100 - (100 / (1 + rs))

# ── MACD(12,26,9) ─────────────────────────────────────
df['ema12'] = ema(df['close'], 12)
df['ema26'] = ema(df['close'], 26)
df['dif'] = df['ema12'] - df['ema26']
df['dea'] = ema(df['dif'], 9)
df['macd_bar'] = 2 * (df['dif'] - df['dea'])

# 金叉/死叉
prev_dif = df['dif'].shift(1)
prev_dea = df['dea'].shift(1)
golden = (df['dif'] > df['dea']) & (prev_dif <= prev_dea)
dead = (df['dif'] < df['dea']) & (prev_dif >= prev_dea)
golden_dates = df[golden]
dead_dates = df[dead]

# ── Bollinger Bands(20,±2σ) ──────────────────────────
df['bb_ma'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std(ddof=1)
df['bb_upper'] = df['bb_ma'] + 2 * df['bb_std']
df['bb_lower'] = df['bb_ma'] - 2 * df['bb_std']
df['bb_bw'] = (df['bb_upper'] - df['bb_lower']) / df['bb_ma']
df['bb_pctb'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

# ── ATR(14) ───────────────────────────────────────────
prev_close = df['close'].shift(1)
tr1 = df['high'] - df['low']
tr2 = (df['high'] - prev_close).abs()
tr3 = (df['low'] - prev_close).abs()
df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
df['atr'] = ema(df['tr'], 14)

print("Indicators calculated. OK")

# ========================
# HTML 模板
# ========================
HTML_HEADER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="plotly.min.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; background:#f5f6fa; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%); color:white; padding:20px 32px; }}
  .header h1 {{ font-size:20px; font-weight:600; }}
  .header p {{ font-size:13px; opacity:0.7; margin-top:4px; }}
  .stats {{ display:flex; gap:16px; padding:16px 32px; background:white; border-bottom:1px solid #e8e8e8; }}
  .stat-item {{ display:flex; flex-direction:column; }}
  .stat-label {{ font-size:11px; color:#999; }}
  .stat-value {{ font-size:18px; font-weight:700; }}
  .chart {{ margin:16px 32px 32px; background:white; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.06); padding:16px; }}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <p>兆易创新 (603986.SH) | 数据范围: {date_from} ~ {date_to} | 复权: 前复权 (qfq) | 数据源: akshare (Sina)</p>
</div>
<div class="stats">
  <div class="stat-item"><span class="stat-label">最新收盘价</span><span class="stat-value" style="color:#e83939">{close}</span></div>
  <div class="stat-item"><span class="stat-label">最高价 (区间)</span><span class="stat-value">{high}</span></div>
  <div class="stat-item"><span class="stat-label">最低价 (区间)</span><span class="stat-value" style="color:#2ba350">{low}</span></div>
  <div class="stat-item"><span class="stat-label">交易日数</span><span class="stat-value">{days}</span></div>
</div>
<div class="chart" id="main-chart" style="height:{chart_height}px;"></div>
<script>
{chart_js}
</script>
</body>
</html>"""

def save_plotly_html(fig, filename, title, chart_height=550):
    """将 Plotly figure 保存为独立 HTML"""
    date_from = df['trade_date'].min().strftime('%Y-%m-%d')
    date_to = df['trade_date'].max().strftime('%Y-%m-%d')
    latest = df.iloc[-1]
    
    chart_json = fig.to_json()
    chart_js = f"var data = {chart_json}; Plotly.newPlot('main-chart', data.data, data.layout, {{responsive:true}});"
    
    html = HTML_HEADER.format(
        title=title,
        date_from=date_from,
        date_to=date_to,
        close=f"{latest['close']:.2f}",
        high=f"{df['high'].max():.2f}",
        low=f"{df['low'].min():.2f}",
        days=len(df),
        chart_height=chart_height,
        chart_js=chart_js
    )
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  [OK] {filename}")

# ========================
# 1. RSI 图表
# ========================
fig_rsi = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.08, row_heights=[0.6, 0.4],
    subplot_titles=('收盘价', 'RSI(14)')
)
fig_rsi.add_trace(go.Scatter(x=df['trade_date'], y=df['close'], mode='lines', name='Close',
    line=dict(color='#333333', width=1.5)), row=1, col=1)
fig_rsi.add_trace(go.Scatter(x=df['trade_date'], y=df['rsi'], mode='lines', name='RSI(14)',
    line=dict(color='#378add', width=1.5)), row=2, col=1)
fig_rsi.add_hline(y=70, line=dict(color='#e83939', dash='dash', width=1), row=2, col=1)
fig_rsi.add_hline(y=30, line=dict(color='#2ba350', dash='dash', width=1), row=2, col=1)
fig_rsi.add_hline(y=50, line=dict(color='#999999', dash='dot', width=0.8), row=2, col=1)
fig_rsi.add_hrect(y0=70, y1=100, fillcolor='#e83939', opacity=0.05, line_width=0, row=2, col=1)
fig_rsi.add_hrect(y0=0, y1=30, fillcolor='#2ba350', opacity=0.05, line_width=0, row=2, col=1)
fig_rsi.update_layout(template='plotly_white', hovermode='x unified', showlegend=False)
fig_rsi.update_yaxes(title_text='价格 (元)', row=1, col=1)
fig_rsi.update_yaxes(title_text='RSI', range=[0, 100], row=2, col=1)
save_plotly_html(fig_rsi, './图表_RSI.html', 'RSI(14) 相对强弱指数', 600)

# ========================
# 2. MACD 图表
# ========================
fig_macd = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.05, row_heights=[0.55, 0.45],
    subplot_titles=('收盘价 & EMA 双线', 'MACD(12,26,9)')
)
fig_macd.add_trace(go.Scatter(x=df['trade_date'], y=df['close'], mode='lines', name='Close',
    line=dict(color='#333333', width=1.2)), row=1, col=1)
fig_macd.add_trace(go.Scatter(x=df['trade_date'], y=df['ema12'], mode='lines', name='EMA(12)',
    line=dict(color='#e83939', width=1)), row=1, col=1)
fig_macd.add_trace(go.Scatter(x=df['trade_date'], y=df['ema26'], mode='lines', name='EMA(26)',
    line=dict(color='#378add', width=1)), row=1, col=1)

colors_bar = ['#e83939' if v >= 0 else '#2ba350' for v in df['macd_bar']]
fig_macd.add_trace(go.Bar(x=df['trade_date'], y=df['macd_bar'], name='BAR',
    marker_color=colors_bar, opacity=0.7), row=2, col=1)
fig_macd.add_trace(go.Scatter(x=df['trade_date'], y=df['dif'], mode='lines', name='DIF',
    line=dict(color='#e83939', width=1.2)), row=2, col=1)
fig_macd.add_trace(go.Scatter(x=df['trade_date'], y=df['dea'], mode='lines', name='DEA',
    line=dict(color='#378add', width=1.2)), row=2, col=1)

if len(golden_dates) > 0:
    fig_macd.add_trace(go.Scatter(x=golden_dates['trade_date'], y=golden_dates['dif'],
        mode='markers', name='金叉', marker=dict(symbol='triangle-up', size=10, color='#e83939')), row=2, col=1)
if len(dead_dates) > 0:
    fig_macd.add_trace(go.Scatter(x=dead_dates['trade_date'], y=dead_dates['dif'],
        mode='markers', name='死叉', marker=dict(symbol='triangle-down', size=10, color='#2ba350')), row=2, col=1)
fig_macd.add_hline(y=0, line=dict(color='#999999', dash='dot', width=0.8), row=2, col=1)

fig_macd.update_layout(template='plotly_white', hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5))
fig_macd.update_yaxes(title_text='价格 (元)', row=1, col=1)
fig_macd.update_yaxes(title_text='MACD', row=2, col=1)
save_plotly_html(fig_macd, './图表_MACD.html', 'MACD(12,26,9) 金叉/死叉', 650)

# ========================
# 3. 布林带图表
# ========================
fig_bb = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.08, row_heights=[0.6, 0.4],
    subplot_titles=('布林带(20,±2σ)', '带宽 (Bandwidth)')
)
fig_bb.add_trace(go.Candlestick(x=df['trade_date'], open=df['open'], high=df['high'],
    low=df['low'], close=df['close'], name='K线',
    increasing_line_color='#e83939', decreasing_line_color='#2ba350', showlegend=False), row=1, col=1)

for name, col, color, dash in [('中轨 MA(20)', 'bb_ma', '#378add', 'solid'),
                                 ('上轨 +2σ', 'bb_upper', '#e83939', 'dash'),
                                 ('下轨 -2σ', 'bb_lower', '#2ba350', 'dash')]:
    fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df[col], mode='lines', name=name,
        line=dict(color=color, width=1.2, dash=dash)), row=1, col=1)

fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['bb_upper'],
    mode='lines', line=dict(width=0), showlegend=False), row=1, col=1)
fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['bb_lower'],
    mode='lines', fill='tonexty', fillcolor='rgba(55,138,221,0.08)',
    line=dict(width=0), showlegend=False), row=1, col=1)

fig_bb.add_trace(go.Scatter(x=df['trade_date'], y=df['bb_bw'], mode='lines', name='带宽',
    line=dict(color='#378add', width=1.5), fill='tozeroy', fillcolor='rgba(55,138,221,0.1)'), row=2, col=1)

fig_bb.update_layout(template='plotly_white', hovermode='x unified')
fig_bb.update_yaxes(title_text='价格 (元)', row=1, col=1)
fig_bb.update_yaxes(title_text='带宽比率', row=2, col=1)
save_plotly_html(fig_bb, './图表_布林带.html', 'Bollinger Bands(20,±2σ) 布林带', 650)

# ========================
# 4. ATR 图表
# ========================
fig_atr = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.08, row_heights=[0.55, 0.45],
    subplot_titles=('K线走势', 'ATR(14) 平均真实波幅')
)
fig_atr.add_trace(go.Candlestick(x=df['trade_date'], open=df['open'], high=df['high'],
    low=df['low'], close=df['close'], name='K线',
    increasing_line_color='#e83939', decreasing_line_color='#2ba350', showlegend=False), row=1, col=1)

fig_atr.add_trace(go.Scatter(x=df['trade_date'], y=df['atr'], mode='lines', name='ATR(14)',
    line=dict(color='#e83939', width=1.8), fill='tozeroy', fillcolor='rgba(232,57,57,0.08)'), row=2, col=1)

atr_mean = df['atr'].mean()
fig_atr.add_hline(y=atr_mean, line=dict(color='#378add', dash='dash', width=1),
    annotation_text=f'均值 {atr_mean:.2f}', row=2, col=1)

fig_atr.update_layout(template='plotly_white', hovermode='x unified')
fig_atr.update_yaxes(title_text='价格 (元)', row=1, col=1)
fig_atr.update_yaxes(title_text='ATR', row=2, col=1)
save_plotly_html(fig_atr, './图表_ATR.html', 'ATR(14) 平均真实波幅', 600)

# ========================
# 5. 综合面板
# ========================
fig_all = make_subplots(
    rows=5, cols=1, shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.3, 0.18, 0.18, 0.18, 0.16],
    subplot_titles=('收盘价', 'RSI(14)', 'MACD(12,26,9)', '布林带(20,±2σ)', 'ATR(14)')
)

fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['close'], mode='lines', name='Close',
    line=dict(color='#333333', width=1.5)), row=1, col=1)

fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['rsi'], mode='lines', name='RSI',
    line=dict(color='#378add', width=1.2)), row=2, col=1)
fig_all.add_hline(y=70, line=dict(color='#e83939', dash='dash', width=0.8), row=2, col=1)
fig_all.add_hline(y=30, line=dict(color='#2ba350', dash='dash', width=0.8), row=2, col=1)
fig_all.add_hrect(y0=70, y1=100, fillcolor='#e83939', opacity=0.05, line_width=0, row=2, col=1)
fig_all.add_hrect(y0=0, y1=30, fillcolor='#2ba350', opacity=0.05, line_width=0, row=2, col=1)

fig_all.add_trace(go.Bar(x=df['trade_date'], y=df['macd_bar'], name='BAR',
    marker_color=['#e83939' if v >= 0 else '#2ba350' for v in df['macd_bar']], opacity=0.6), row=3, col=1)
fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['dif'], mode='lines', name='DIF',
    line=dict(color='#e83939', width=1)), row=3, col=1)
fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['dea'], mode='lines', name='DEA',
    line=dict(color='#378add', width=1)), row=3, col=1)
fig_all.add_hline(y=0, line=dict(color='#999', dash='dot', width=0.5), row=3, col=1)

fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['bb_upper'], mode='lines', name='BB上轨',
    line=dict(color='#e83939', width=0.8, dash='dash')), row=4, col=1)
fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['bb_ma'], mode='lines', name='BB中轨',
    line=dict(color='#378add', width=1)), row=4, col=1)
fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['bb_lower'], mode='lines', name='BB下轨',
    line=dict(color='#2ba350', width=0.8, dash='dash')), row=4, col=1)
fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['close'], mode='lines', name='Close',
    line=dict(color='#333', width=1.2), showlegend=False), row=4, col=1)

fig_all.add_trace(go.Scatter(x=df['trade_date'], y=df['atr'], mode='lines', name='ATR',
    line=dict(color='#e83939', width=1.2), fill='tozeroy', fillcolor='rgba(232,57,57,0.06)'), row=5, col=1)
fig_all.add_hline(y=atr_mean, line=dict(color='#378add', dash='dash', width=0.8), row=5, col=1)

fig_all.update_layout(
    template='plotly_white', hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5)
)
for row, title in [(1, '价格 (元)'), (2, 'RSI'), (3, 'MACD'), (4, '价格 (元)'), (5, 'ATR')]:
    fig_all.update_yaxes(title_text=title, row=row, col=1)

save_plotly_html(fig_all, './图表_四指标综合面板.html', '四指标综合面板', 1100)

print("\nAll charts generated! Open HTML files in browser.")
