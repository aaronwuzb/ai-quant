# -*- coding: utf-8 -*-
"""
gen_indicator_panel_v3.py
纯 Python+JS 分离架构，避免 f-string 与 JS template literal 转义冲突。
读取 CSV → 计算四指标 → 生成独立 HTML 面板。
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
CSV_PATH  = BASE_DIR / '中芯国际_hk00981_近一年数据.csv'
HTML_PATH = Path(__file__).parent / '中芯国际_技术指标面板.html'

R = '#e83939'
G = '#2ba350'
B = '#378add'

# ==========================================================
# 1. 数据加载
# ==========================================================
df = pd.read_csv(CSV_PATH)
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date').sort_index()

close = df['close'].values
high  = df['high'].values
low   = df['low'].values
open_ = df['open'].values
volume = df['volume'].values
n = len(df)
dates_str = [d.strftime('%Y-%m-%d') for d in df.index]

print(f"[1/4] 数据加载: {n} 条, {dates_str[0]} ~ {dates_str[-1]}")

# ==========================================================
# 2. 指标计算
# ==========================================================

def ema(arr, span):
    return pd.Series(arr).ewm(span=span, adjust=False).mean().values

# RSI(14)
delta = np.diff(close, prepend=close[0])
gain = np.where(delta > 0, delta, 0)
loss = np.where(delta < 0, -delta, 0)
rsi = 100 - 100 / (1 + pd.Series(gain).rolling(14).mean().values /
                         pd.Series(loss).rolling(14).mean().values)

# MACD(12,26,9)
ema12 = ema(close, 12)
ema26 = ema(close, 26)
dif = ema12 - ema26
dea = ema(dif, 9)
macd_bar = 2 * (dif - dea)

# 金叉/死叉
golden, dead = [], []
for i in range(1, n):
    if dif[i-1] <= dea[i-1] and dif[i] > dea[i]:
        golden.append(i)
    elif dif[i-1] >= dea[i-1] and dif[i] < dea[i]:
        dead.append(i)

# Bollinger Bands(20,2)
bb_mid = pd.Series(close).rolling(20).mean().values
bb_std = pd.Series(close).rolling(20).std(ddof=1).values
bb_upper = bb_mid + 2 * bb_std
bb_lower = bb_mid - 2 * bb_std
bb_pct_b = (close - bb_lower) / (bb_upper - bb_lower)

# ATR(14)
tr = np.zeros(n)
for i in range(1, n):
    tr[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
atr = ema(tr, 14)

print(f"[2/4] 指标计算完成: RSI/MACD/BB/ATR")

# ==========================================================
# 3. 数据序列化 (清除 NaN → null)
# ==========================================================
def arr(arr_in, decimals=2):
    """Convert numpy array to list, NaN→None for JSON serialization"""
    result = []
    for x in arr_in:
        if np.isnan(x):
            result.append(None)
        else:
            result.append(round(float(x), decimals))
    return result

def arr_int(arr_in):
    return [int(x) for x in arr_in]

data = {
    "dates":     dates_str,
    "open":      arr(open_),
    "high":      arr(high),
    "low":       arr(low),
    "close":     arr(close),
    "volume":    arr_int(volume),
    "rsi":       arr(rsi),
    "dif":       arr(dif),
    "dea":       arr(dea),
    "bar":       arr(macd_bar),
    "bb_mid":    arr(bb_mid),
    "bb_upper":  arr(bb_upper),
    "bb_lower":  arr(bb_lower),
    "bb_pct_b":  arr(bb_pct_b),
    "atr":       arr(atr),
    "golden":    [dates_str[i] for i in golden],
    "dead":      [dates_str[i] for i in dead],
    "summary": {
        "date":        dates_str[-1],
        "close":       round(float(close[-1]), 2),
        "chg_pct":     round(float((close[-1]-close[-2])/close[-2]*100), 2),
        "rsi":         round(float(rsi[-1]), 2),
        "rsi_signal":  "超买" if rsi[-1]>70 else ("超卖" if rsi[-1]<30 else "中性"),
        "dif":         round(float(dif[-1]), 2),
        "dea":         round(float(dea[-1]), 2),
        "bar":         round(float(macd_bar[-1]), 2),
        "macd_signal": "多头" if dif[-1] > dea[-1] else "空头",
        "golden_count": len(golden),
        "dead_count":   len(dead),
        "bb_mid":      round(float(bb_mid[-1]), 2),
        "bb_upper":    round(float(bb_upper[-1]), 2),
        "bb_lower":    round(float(bb_lower[-1]), 2),
        "bb_pct_b":    round(float(bb_pct_b[-1]), 2),
        "bb_signal":   "突破上轨" if close[-1]>bb_upper[-1] else ("跌破下轨" if close[-1]<bb_lower[-1] else "带内"),
        "atr":         round(float(atr[-1]), 2),
        "atr_pct":     round(float(atr[-1]/close[-1]*100), 2),
        "mean_atr":    round(float(np.mean(atr[~np.isnan(atr)])), 2),
    }
}

data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
print(f"[3/4] JSON 序列化: {len(data_json)} 字符")

# ==========================================================
# 4. HTML 模板 (纯静态 JS，Python 不做任何 f-string 转义)
# ==========================================================
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>中芯国际 (00981.HK) 技术指标面板</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.3/plotly.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;background:#f5f7fa;color:#1a1a2e}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:24px 36px}
.header h1{font-size:22px;margin-bottom:4px}
.header .sub{font-size:13px;opacity:.65}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:16px 36px}
.card{background:#fff;border-radius:8px;padding:16px 20px;box-shadow:0 1px 6px rgba(0,0,0,.06)}
.card .label{font-size:12px;color:#999;margin-bottom:4px}
.card .value{font-size:24px;font-weight:700}
.card .tag{font-size:11px;margin-top:4px;padding:2px 8px;border-radius:3px;display:inline-block}
.up{color:COLOR_RED;background:#fde8e8}
.down{color:COLOR_GREEN;background:#e6f5ea}
.neutral{color:#888;background:#eee}
.chart-box{margin:0 36px 16px;background:#fff;border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.06);overflow:hidden}
.chart-box .title{padding:14px 18px;font-size:14px;font-weight:700;border-bottom:1px solid #f0f0f0}
.chart-box .plot{padding:8px}
.footer{text-align:center;padding:24px;font-size:12px;color:#bbb}
</style>
</head>
<body>

<div class="header">
  <h1>中芯国际 (00981.HK) · 技术指标面板</h1>
  <div class="sub">数据范围: __DATE_START__ ~ __DATE_END__ (__COUNT__ 交易日) | 前复权(qfq) | akshare(Sina)</div>
</div>

<div class="cards" id="cards"></div>

<div class="chart-box"><div class="title">K 线 & 成交量</div><div class="plot" id="chart_kl" style="height:460px"></div></div>
<div class="chart-box"><div class="title">RSI(14) — 相对强弱指数</div><div class="plot" id="chart_rsi" style="height:380px"></div></div>
<div class="chart-box"><div class="title">MACD(12,26,9) — 金叉 / 死叉</div><div class="plot" id="chart_macd" style="height:440px"></div></div>
<div class="chart-box"><div class="title">Bollinger Bands(20,2) — 布林带</div><div class="plot" id="chart_bb" style="height:440px"></div></div>
<div class="chart-box"><div class="title">ATR(14) — 平均真实波幅</div><div class="plot" id="chart_atr" style="height:380px"></div></div>

<div class="footer">免责声明: 仅供学习参考，不构成投资建议。技术指标基于历史数据，不预测未来走势。</div>

<script>
// ══════ 颜色常量 ══════
var RED = "COLOR_RED";
var GREEN = "COLOR_GREEN";
var BLUE = "COLOR_BLUE";

// ══════ 核心数据 ══════
var D = __DATA_PLACEHOLDER__;

// ══════ 通用模板 ══════
var tpl = {
  paper_bgcolor:"white", plot_bgcolor:"white",
  font:{family:"Microsoft YaHei,PingFang SC,sans-serif",color:"#333"},
  xaxis:{showgrid:false}, yaxis:{showgrid:true,gridcolor:"#f0f0f0"},
  hovermode:"x unified"
};

// ══════ 概要卡片 ══════
(function renderCards(){
  var s = D.summary;

  function tagCls(val, upThresh, downThresh){
    if(upThresh !== undefined && val > upThresh) return "up";
    if(downThresh !== undefined && val < downThresh) return "down";
    return "neutral";
  }

  var clsClose = s.chg_pct >= 0 ? "up" : "down";
  var clsRsi   = s.rsi > 70 ? "up" : (s.rsi < 30 ? "down" : "neutral");
  var clsMacd  = s.macd_signal === "多头" ? "up" : "down";
  var clsAtr   = s.atr > s.mean_atr * 1.2 ? "up" : (s.atr < s.mean_atr * 0.8 ? "down" : "neutral");

  document.getElementById("cards").innerHTML =
    '<div class="card">' +
      '<div class="label">收盘价</div>' +
      '<div class="value" style="color:'+ (s.chg_pct>=0?RED:GREEN) +'">HK$'+ s.close +'</div>' +
      '<div class="tag '+ clsClose +'">'+ (s.chg_pct>=0?"+":"") + s.chg_pct +'%</div>' +
    '</div>' +
    '<div class="card">' +
      '<div class="label">RSI(14)</div>' +
      '<div class="value">'+ s.rsi +'</div>' +
      '<div class="tag '+ clsRsi +'">'+ s.rsi_signal +'</div>' +
    '</div>' +
    '<div class="card">' +
      '<div class="label">MACD</div>' +
      '<div class="value" style="font-size:20px">DIF '+ s.dif +'</div>' +
      '<div class="tag '+ clsMacd +'">'+ s.macd_signal +' | '+ s.golden_count +'金/'+ s.dead_count +'死</div>' +
    '</div>' +
    '<div class="card">' +
      '<div class="label">ATR(14) 日波幅</div>' +
      '<div class="value">HK$'+ s.atr +'</div>' +
      '<div class="tag '+ clsAtr +'">占收盘 '+ s.atr_pct +'% | '+ (s.atr > s.mean_atr*1.2?"高波动":(s.atr < s.mean_atr*0.8?"低波动":"正常")) +'</div>' +
    '</div>';
})();

// ══════ 1. K 线 + 成交量 ══════
(function(){
  var colors = D.close.map(function(c,i){ return c >= D.open[i] ? RED : GREEN; });
  Plotly.newPlot("chart_kl", [
    { x:D.dates, open:D.open, high:D.high, low:D.low, close:D.close,
      type:"candlestick", name:"OHLC",
      increasing:{line:{color:RED}}, decreasing:{line:{color:GREEN}},
      hoverinfo:"x+text" },
    { x:D.dates, y:D.volume, type:"bar", name:"成交量", yaxis:"y2",
      marker:{color: D.close.map(function(c,i){
        return "rgba("+ (c>=D.open[i]?"232,57,57":"43,163,80") +",0.4)"; }) }}
  ], Object.assign({}, tpl, {
    title:"中芯国际 (00981.HK) K 线 & 成交量",
    yaxis:{title:"价格 (HKD)", domain:[0.25,1]},
    yaxis2:{title:"成交量 (股)", domain:[0,0.2], showgrid:false},
    xaxis:{rangeslider:{visible:false}},
    height:460
  }));
})();

// ══════ 2. RSI(14) ══════
(function(){
  Plotly.newPlot("chart_rsi", [
    { x:D.dates, y:D.rsi, type:"scatter", mode:"lines", name:"RSI(14)",
      line:{color:RED,width:2}, fill:"tozeroy", fillcolor:"rgba(232,57,57,0.06)" }
  ], Object.assign({}, tpl, {
    title:"RSI(14) — 超买线 70 | 超卖线 30",
    yaxis:{title:"RSI", range:[0,100]},
    shapes:[
      {type:"line",x0:D.dates[0],x1:D.dates[D.dates.length-1],y0:70,y1:70,
       line:{dash:"dash",color:RED,width:1.2}},
      {type:"line",x0:D.dates[0],x1:D.dates[D.dates.length-1],y0:30,y1:30,
       line:{dash:"dash",color:GREEN,width:1.2}},
      {type:"line",x0:D.dates[0],x1:D.dates[D.dates.length-1],y0:50,y1:50,
       line:{dash:"dot",color:"gray",width:0.6,opacity:0.4}}
    ],
    height:380
  }));
})();

// ══════ 3. MACD(12,26,9) ══════
(function(){
  var barColors = D.bar.map(function(v){ return v===null?"transparent":(v>=0?RED:GREEN); });
  Plotly.newPlot("chart_macd", [
    { x:D.dates, y:D.bar, type:"bar", name:"BAR", marker:{color:barColors} },
    { x:D.dates, y:D.dif, type:"scatter", mode:"lines", name:"DIF",
      line:{color:RED,width:1.5} },
    { x:D.dates, y:D.dea, type:"scatter", mode:"lines", name:"DEA",
      line:{color:BLUE,width:1.5} },
    { x:D.golden, y:D.golden.map(function(d){return D.dif[D.dates.indexOf(d)]}),
      type:"scatter", mode:"markers", name:"金叉",
      marker:{symbol:"triangle-up",size:11,color:RED,line:{width:1,color:"white"}} },
    { x:D.dead, y:D.dead.map(function(d){return D.dif[D.dates.indexOf(d)]}),
      type:"scatter", mode:"markers", name:"死叉",
      marker:{symbol:"triangle-down",size:11,color:GREEN,line:{width:1,color:"white"}} }
  ], Object.assign({}, tpl, {
    title:"MACD(12,26,9) — BAR / DIF / DEA",
    yaxis:{title:"MACD"},
    shapes:[{type:"line",x0:D.dates[0],x1:D.dates[D.dates.length-1],y0:0,y1:0,
             line:{dash:"dot",color:"gray",width:0.6,opacity:0.4}}],
    height:440
  }));
})();

// ══════ 4. Bollinger Bands(20,2) ══════
(function(){
  Plotly.newPlot("chart_bb", [
    { x:D.dates, y:D.close, type:"scatter", mode:"lines", name:"Close",
      line:{color:"#333",width:1.5} },
    { x:D.dates, y:D.bb_upper, type:"scatter", mode:"lines", name:"上轨 MA+2σ",
      line:{color:RED,width:1,dash:"dash"} },
    { x:D.dates, y:D.bb_mid, type:"scatter", mode:"lines", name:"中轨 MA(20)",
      line:{color:BLUE,width:1.2} },
    { x:D.dates, y:D.bb_lower, type:"scatter", mode:"lines", name:"下轨 MA-2σ",
      line:{color:GREEN,width:1,dash:"dash"},
      fill:"tonexty", fillcolor:"rgba(135,206,250,0.08)" }
  ], Object.assign({}, tpl, {
    title:"Bollinger Bands(20,2)",
    yaxis:{title:"价格 (HKD)"},
    height:440
  }));
})();

// ══════ 5. ATR(14) ══════
(function(){
  Plotly.newPlot("chart_atr", [
    { x:D.dates, y:D.atr, type:"scatter", mode:"lines", name:"ATR(14)",
      line:{color:RED,width:2}, fill:"tozeroy", fillcolor:"rgba(232,57,57,0.08)" }
  ], Object.assign({}, tpl, {
    title:"ATR(14) 波动率指标",
    yaxis:{title:"HKD"},
    height:380
  }));
})();
</script>
</body>
</html>'''

# ==========================================================
# 5. 注入数据 & 写入文件
# ==========================================================
html = HTML_TEMPLATE
html = html.replace('__DATA_PLACEHOLDER__', data_json)
html = html.replace('__DATE_START__', dates_str[0])
html = html.replace('__DATE_END__', dates_str[-1])
html = html.replace('__COUNT__', str(n))
html = html.replace('COLOR_RED', R)
html = html.replace('COLOR_GREEN', G)
html = html.replace('COLOR_BLUE', B)

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

size_kb = HTML_PATH.stat().st_size // 1024
print(f"[4/4] 面板生成: {HTML_PATH} ({size_kb} KB)")
print(f"       数据: {n} 条 | {len(golden)} 金叉 {len(dead)} 死叉 | 收盘 {close[-1]:.2f}")
