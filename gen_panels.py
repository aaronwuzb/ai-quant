"""
gen_panels.py — 统一 HTML 分析面板生成脚本 (v2.0)
从标准 JSON 文件读取 L1 数据，生成 Plotly 交互式 HTML 面板。

功能:
  - 单股票 K 线分析面板 (含除权标注)
  - AH 股对比分析面板
  - 自动检测 AH 类型
  - 动态金额单位 (万/亿)
  - 除权日自动检测与标注
"""

import json, os

# ============================================================
# 配置
# ============================================================

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
RED         = "#e83939"
GREEN       = "#2ba350"
BLUE        = "#378add"
HKD_CNY     = 0.91

STOCKS = {
    "中芯国际": {"a_code": "sh688981", "h_code": "hk00981", "has_h": True},
    "比亚迪":   {"a_code": "sz002594", "h_code": "hk01211", "has_h": True},
    "长江电力":  {"a_code": "sh600900", "h_code": None,      "has_h": False},
}

# ============================================================
# 工具函数
# ============================================================

def load(name: str, code: str) -> dict | None:
    """加载 JSON 数据文件，兼容新旧两种格式"""
    path = os.path.join(SCRIPT_DIR, f"{name}_{code}_近一年数据.json")
    if not os.path.exists(path):
        print(f"  [WARN] 文件不存在: {path}")
        return None
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    # 新格式: {"_meta": {...}, "data": [...]}
    # 旧格式: [...]
    if isinstance(raw, dict) and "data" in raw:
        return raw["data"]
    return raw


def fmt_amount(val: float, unit: str = "元") -> str:
    """动态金额格式化: >=1亿 → X.X亿, >=1万 → X.X万, <1万 → 整数"""
    if abs(val) >= 1e8:
        return f"{unit}{val/1e8:.1f}亿"
    elif abs(val) >= 1e4:
        return f"{unit}{val/1e4:.1f}万"
    else:
        return f"{unit}{val:.0f}"


def detect_ex_rights(data: list[dict]) -> list[str]:
    """检测除权除息日: 单日 open vs 前日 close 跳变 > 30%"""
    ex_dates = []
    for i in range(1, len(data)):
        prev_c = data[i-1]["close"]
        curr_o = data[i]["open"]
        if prev_c and abs((curr_o - prev_c) / prev_c) > 0.30:
            ex_dates.append(data[i]["date"])
    return ex_dates


def compute_stats(data: list[dict]):
    """计算面板所需统计指标"""
    n = len(data)
    if n < 2:
        return None

    dates = [d["date"] for d in data]
    opens = [d["open"] for d in data]
    closes = [d["close"] for d in data]
    highs = [d["high"] for d in data]
    lows = [d["low"] for d in data]
    volumes = [d["volume"] for d in data]
    amounts = [d["amount"] for d in data]

    fc, lc = closes[0], closes[-1]
    chg = (lc - fc) / fc * 100 if fc else 0
    mhi, mlo = max(highs), min(lows)
    mhd = dates[highs.index(mhi)]
    mld = dates[lows.index(mlo)]
    avg_vol = sum(volumes) / n
    avg_amt = sum(amounts) / n

    up = sum(1 for i in range(1, n) if closes[i] > closes[i-1])
    dn = n - 1 - up

    rets = [(closes[i] - closes[i-1]) / closes[i-1]
            for i in range(1, n) if closes[i-1] != 0]
    daily_vol = (sum((r - sum(rets)/len(rets))**2 for r in rets) / len(rets))**0.5 if rets else 0

    # 最大回撤
    peak = closes[0]; max_dd = 0.0
    for c in closes:
        if c > peak:
            peak = c
        dd = (peak - c) / peak * 100
        if dd > max_dd:
            max_dd = dd

    return {
        "n": n, "dates": dates, "opens": opens, "closes": closes,
        "highs": highs, "lows": lows, "volumes": volumes, "amounts": amounts,
        "fc": fc, "lc": lc, "chg": chg,
        "mhi": mhi, "mlo": mlo, "mhd": mhd, "mld": mld,
        "avg_vol": avg_vol, "avg_amt": avg_amt,
        "up": up, "dn": dn, "daily_vol": daily_vol, "max_dd": max_dd,
    }


# ============================================================
# 单股票 K 线面板
# ============================================================

def single_panel(name: str, code: str, data: list[dict],
                 ex_dates: list[str] = None,
                 extra_note: str = "") -> str:
    """生成单股票 K 线分析面板"""
    s = compute_stats(data)
    if not s:
        return None

    ex_dates = ex_dates or detect_ex_rights(data)
    ex_note = ""
    if ex_dates:
        ex_note = f" | 含除权日: {', '.join(ex_dates)}"

    # 生成除权标记 JavaScript
    ex_js = ""
    if ex_dates:
        ex_js = "\n".join([
            "{type:'scatter',x:['%s'],y:[%.2f],mode:'markers+text',"
            "marker:{color:'#ff6600',size:12,symbol:'x-thin'},"
            "text:['除权日'],textposition:'top center',name:'除权'}" %
            (ed, dict(zip(s["dates"], s["highs"]))[ed] if ed in s["dates"] else s["highs"][0])
            for ed in ex_dates if ed in s["dates"]
        ])

    panel_file = os.path.join(SCRIPT_DIR, f"{name}_K线分析面板.html")
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{name} ({code}) 近一年日线分析</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.2/plotly.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#333;padding:20px}}
h1{{font-size:22px;font-weight:500;margin-bottom:4px}}
.sub{{font-size:13px;color:#888;margin-bottom:20px}}
.cards{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:20px}}
.card{{background:#fff;border-radius:8px;padding:14px 16px;border:1px solid #eee}}
.clabel{{font-size:11px;color:#999;margin-bottom:4px}}
.cval{{font-size:18px;font-weight:500}}
.csub{{font-size:11px;color:#888;margin-top:2px}}
.red{{color:#e83939}}.green{{color:#2ba350}}
.section{{background:#fff;border-radius:8px;padding:16px;border:1px solid #eee;margin-bottom:16px}}
.stitle{{font-size:14px;font-weight:500;margin-bottom:8px;color:#555}}
.analysis{{background:#fff;border-radius:8px;padding:16px;border:1px solid #eee;margin-bottom:16px;display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.acol h3{{font-size:13px;font-weight:500;margin-bottom:8px;color:#555}}
.aitem{{display:flex;justify-content:space-between;padding:4px 0;font-size:12px;border-bottom:1px solid #f0f0f0}}
.aitem:last-child{{border-bottom:none}}
.disclaimer{{background:#fff;border-radius:8px;padding:16px;border:1px solid #eee}}
.disclaimer h3{{font-size:13px;font-weight:500;color:#e83939;margin-bottom:8px}}
.disclaimer p{{font-size:12px;color:#666;padding:2px 0;line-height:1.6}}
.ex-note{{display:inline-block;background:#fff3e0;color:#e65100;font-size:12px;padding:2px 8px;border-radius:4px;margin-left:8px}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(3,1fr)}}.analysis{{grid-template-columns:1fr}}}}
</style></head>
<body>
<h1>{name} ({code}) 近一年日线分析</h1>
<div class="sub">数据区间: {s['dates'][0]} ~ {s['dates'][-1]} | {s['n']}个交易日 | 前复权 (qfq){ex_note}{extra_note}</div>

<div class="cards">
<div class="card"><div class="clabel">最新收盘价</div><div class="cval">¥{s['lc']:.2f}</div><div class="csub">{s['dates'][-1]}</div></div>
<div class="card"><div class="clabel">累计涨跌幅</div><div class="cval {'red' if s['chg']>0 else 'green'}">{s['chg']:+.2f}%</div><div class="csub">起始 ¥{s['fc']:.2f}</div></div>
<div class="card"><div class="clabel">区间最高</div><div class="cval red">¥{s['mhi']:.2f}</div><div class="csub">{s['mhd']}</div></div>
<div class="card"><div class="clabel">区间最低</div><div class="cval green">¥{s['mlo']:.2f}</div><div class="csub">{s['mld']}</div></div>
<div class="card"><div class="clabel">日均成交量</div><div class="cval">{s['avg_vol']/1e4:.0f}<span style="font-size:12px">万手</span></div><div class="csub">日均额 {fmt_amount(s['avg_amt'])}</div></div>
<div class="card"><div class="clabel">日波动率</div><div class="cval">{s['daily_vol']*100:.2f}%</div><div class="csub">涨{s['up']}天 / 跌{s['dn']}天</div></div>
</div>

<div class="section"><div class="stitle">K 线图 + 成交量</div><div id="kline" style="height:600px"></div></div>
<div class="section"><div class="stitle">每日收盘价走势</div><div id="close-chart" style="height:350px"></div></div>

<div class="analysis">
<div class="acol"><h3>多方因素</h3>
<div class="aitem"><span>最新价 vs 起始价</span><span class="{'red' if s['chg']>0 else 'green'}">{s['chg']:+.1f}%</span></div>
<div class="aitem"><span>上涨天数占比</span><span>{s['up']}/{s['up']+s['dn']} ({s['up']/(s['up']+s['dn'])*100:.0f}%)</span></div>
<div class="aitem"><span>日均成交额</span><span>{fmt_amount(s['avg_amt'])}</span></div></div>
<div class="acol"><h3>风险提示</h3>
<div class="aitem"><span>最大回撤</span><span class="green">-{s['max_dd']:.1f}%</span></div>
<div class="aitem"><span>日波动率(年化)</span><span>{s['daily_vol']*100*(252**0.5):.1f}%</span></div>
<div class="aitem"><span>下跌天数占比</span><span>{s['dn']}/{s['up']+s['dn']} ({s['dn']/(s['up']+s['dn'])*100:.0f}%)</span></div></div>
</div>

<div class="disclaimer"><h3>免责声明</h3>
<p>以上分析仅基于历史数据，不构成任何投资建议。投资有风险，入市需谨慎。</p>
<p>数据来源: akshare (Sina) | 复权方式: 前复权 (qfq){ex_note}</p></div>

<script>
var kd={json.dumps([dict(x=s['dates'][i],open=s['opens'][i],high=s['highs'][i],low=s['lows'][i],close=s['closes'][i]) for i in range(s['n'])],ensure_ascii=False)};
var cd={json.dumps([dict(x=s['dates'][i],y=s['closes'][i]) for i in range(s['n'])],ensure_ascii=False)};
var vd={json.dumps([dict(x=s['dates'][i],y=s['volumes'][i],color=RED if s['closes'][i]>=s['opens'][i] else GREEN) for i in range(s['n'])],ensure_ascii=False)};

var ktraces=[
{{type:'candlestick',x:kd.map(d=>d.x),open:kd.map(d=>d.open),high:kd.map(d=>d.high),low:kd.map(d=>d.low),close:kd.map(d=>d.close),increasing:{{line:{{color:'{RED}'}},fillcolor:'{RED}'}},decreasing:{{line:{{color:'{GREEN}'}},fillcolor:'{GREEN}'}},name:'K线'}},
{{type:'bar',x:vd.map(d=>d.x),y:vd.map(d=>d.y),marker:{{color:vd.map(d=>d.color)}},name:'成交量',yaxis:'y2'}}
];
""" + (f"""
// 除权日标注
ktraces.push({ex_js});
""" if ex_js else "") + f"""
Plotly.newPlot('kline',ktraces,
{{xaxis:{{rangeslider:{{visible:false}},type:'category'}},
yaxis:{{title:'价格(元)',side:'left'}},
yaxis2:{{title:'成交量(手)',overlaying:'y',side:'right',showgrid:false}},
template:'plotly_white',height:600,hovermode:'x unified',legend:{{orientation:'h',y:1.15}}}});

Plotly.newPlot('close-chart',[
{{type:'scatter',x:cd.map(d=>d.x),y:cd.map(d=>d.y),mode:'lines',line:{{color:'{BLUE}',width:2}},name:'收盘价'}},
{{type:'scatter',x:['{s['mhd']}'],y:[{s['mhi']}],mode:'markers+text',marker:{{color:'{RED}',size:10}},text:['最高{s['mhi']:.2f}'],textposition:'top center',name:'最高'}},
{{type:'scatter',x:['{s['mld']}'],y:[{s['mlo']}],mode:'markers+text',marker:{{color:'{GREEN}',size:10}},text:['最低{s['mlo']:.2f}'],textposition:'bottom center',name:'最低'}}
],{{xaxis:{{type:'category'}},yaxis:{{title:'价格(元)'}},template:'plotly_white',height:350,hovermode:'x unified',showlegend:true,legend:{{orientation:'h',y:1.12}}}});
</script></body></html>"""

    with open(panel_file, "w", encoding="utf-8") as f:
        f.write(html)
    return panel_file


# ============================================================
# AH 对比面板
# ============================================================

def ah_panel(name: str, a_code: str, h_code: str,
             a_data: list[dict], h_data: list[dict]) -> str:
    """生成 AH 股对比分析面板"""
    ad = {d["date"]: d for d in a_data}
    hd = {d["date"]: d for d in h_data}
    cm = sorted(set(ad.keys()) & set(hd.keys()))

    if not cm:
        print(f"  [{name}] AH 无重叠交易日，跳过")
        return None

    al = []
    for dt in cm:
        ax = ad[dt]; hx = hd[dt]
        al.append({"date": dt, "ac": ax["close"], "hc": hx["close"]})

    a0 = al[0]["ac"]; h0 = al[0]["hc"] * HKD_CNY
    for x in al:
        x["an"] = x["ac"] / a0 * 100
        x["hn"] = x["hc"] * HKD_CNY / h0 * 100
        x["pr"] = (x["ac"] - x["hc"] * HKD_CNY) / (x["hc"] * HKD_CNY) * 100

    prs = [x["pr"] for x in al]
    ap = sum(prs) / len(prs) if prs else 0
    mxp = max(prs) if prs else 0
    mnp = min(prs) if prs else 0

    af = a_data[0]["close"]; al_ = a_data[-1]["close"]
    ach = (al_ - af) / af * 100 if af else 0
    hf = h_data[0]["close"]; hl_ = h_data[-1]["close"]
    hch = (hl_ - hf) / hf * 100 if hf else 0

    panel_file = os.path.join(SCRIPT_DIR, f"{name}_AH对比分析面板.html")
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{name} AH 股对比分析</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.2/plotly.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;color:#333;padding:20px}}
h1{{font-size:22px;font-weight:500;margin-bottom:4px}}
.sub{{font-size:13px;color:#888;margin-bottom:20px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.card{{background:#fff;border-radius:8px;padding:14px 16px;border:1px solid #eee}}
.clabel{{font-size:11px;color:#999;margin-bottom:4px}}
.cval{{font-size:18px;font-weight:500}}
.csub{{font-size:11px;color:#888;margin-top:2px}}
.red{{color:#e83939}}.green{{color:#2ba350}}
.section{{background:#fff;border-radius:8px;padding:16px;border:1px solid #eee;margin-bottom:16px}}
.stitle{{font-size:14px;font-weight:500;margin-bottom:8px;color:#555}}
.disclaimer{{background:#fff;border-radius:8px;padding:16px;border:1px solid #eee}}
.disclaimer h3{{font-size:13px;font-weight:500;color:#e83939;margin-bottom:8px}}
.disclaimer p{{font-size:12px;color:#666;padding:2px 0;line-height:1.6}}
</style></head>
<body>
<h1>{name} AH 股对比分析面板</h1>
<div class="sub">A股 {a_code} vs 港股 {h_code} | {cm[0]} ~ {cm[-1]} | {len(cm)}个重叠交易日 | 汇率 HKD/CNY={HKD_CNY}</div>

<div class="cards">
<div class="card"><div class="clabel">A股涨跌幅</div><div class="cval {'red' if ach>0 else 'green'}">{ach:+.2f}%</div><div class="csub">¥{af:.2f} → ¥{al_:.2f}</div></div>
<div class="card"><div class="clabel">港股涨跌幅</div><div class="cval {'red' if hch>0 else 'green'}">{hch:+.2f}%</div><div class="csub">HK${hf:.2f} → HK${hl_:.2f}</div></div>
<div class="card"><div class="clabel">AH平均溢价率</div><div class="cval">{ap:+.1f}%</div><div class="csub">最高 {mxp:.1f}% / 最低 {mnp:.1f}%</div></div>
<div class="card"><div class="clabel">重叠交易日</div><div class="cval">{len(cm)}</div><div class="csub">A股{len(a_data)}天 / 港股{len(h_data)}天</div></div>
</div>

<div class="section"><div class="stitle">归一化价格走势对比 (基准=100)</div><div id="nc" style="height:400px"></div></div>
<div class="section"><div class="stitle">AH溢价率走势</div><div id="pc" style="height:350px"></div></div>
<div class="section"><div class="stitle">A股 vs 港股 K线对比</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div id="akl" style="height:400px"></div><div id="hkl" style="height:400px"></div>
</div></div>

<div class="disclaimer"><h3>免责声明</h3>
<p>以上分析仅基于历史数据，不构成任何投资建议。</p>
<p>AH溢价计算汇率: HKD/CNY={HKD_CNY} | 数据来源: akshare (Sina) | 复权方式: 前复权 (qfq)</p></div>

<script>
var al={json.dumps(al,ensure_ascii=False)};
Plotly.newPlot('nc',[
{{x:al.map(d=>d.date),y:al.map(d=>d.an),mode:'lines',name:'A股({a_code})',line:{{color:'{RED}',width:2}}}},
{{x:al.map(d=>d.date),y:al.map(d=>d.hn),mode:'lines',name:'港股({h_code})',line:{{color:'{GREEN}',width:2}}}}
],{{xaxis:{{type:'category'}},yaxis:{{title:'指数(起始=100)'}},template:'plotly_white',height:400,hovermode:'x unified',legend:{{orientation:'h',y:1.12}}}});

Plotly.newPlot('pc',[
{{x:al.map(d=>d.date),y:al.map(d=>d.pr),type:'bar',marker:{{color:al.map(d=>d.pr>=0?'{RED}':'{GREEN}')}},name:'溢价率'}}
],{{xaxis:{{type:'category'}},yaxis:{{title:'溢价率(%)'}},template:'plotly_white',height:350,hovermode:'x unified'}});

// A股 K线
var akd={json.dumps([dict(x=ad[d]['date'],open=ad[d]['open'],high=ad[d]['high'],low=ad[d]['low'],close=ad[d]['close']) for d in cm],ensure_ascii=False)};
var avd={json.dumps([dict(x=ad[d]['date'],y=ad[d]['volume'],color=RED if ad[d]['close']>=ad[d]['open'] else GREEN) for d in cm],ensure_ascii=False)};
Plotly.newPlot('akl',[
{{type:'candlestick',x:akd.map(d=>d.x),open:akd.map(d=>d.open),high:akd.map(d=>d.high),low:akd.map(d=>d.low),close:akd.map(d=>d.close),increasing:{{line:{{color:'{RED}'}},fillcolor:'{RED}'}},decreasing:{{line:{{color:'{GREEN}'}},fillcolor:'{GREEN}'}},name:'A股K线'}},
{{type:'bar',x:avd.map(d=>d.x),y:avd.map(d=>d.y),marker:{{color:avd.map(d=>d.color)}},name:'A股成交量',yaxis:'y2'}}
],{{title:'A股 ({a_code})',xaxis:{{rangeslider:{{visible:false}},type:'category'}},yaxis:{{title:'价格(元)'}},yaxis2:{{title:'成交量',overlaying:'y',side:'right',showgrid:false}},template:'plotly_white',height:400,hovermode:'x unified',legend:{{orientation:'h',y:1.15}}}});

// 港股 K线
var hkd={json.dumps([dict(x=hd[d]['date'],open=hd[d]['open'],high=hd[d]['high'],low=hd[d]['low'],close=hd[d]['close']) for d in cm],ensure_ascii=False)};
var hvd={json.dumps([dict(x=hd[d]['date'],y=hd[d]['volume'],color=RED if hd[d]['close']>=hd[d]['open'] else GREEN) for d in cm],ensure_ascii=False)};
Plotly.newPlot('hkl',[
{{type:'candlestick',x:hkd.map(d=>d.x),open:hkd.map(d=>d.open),high:hkd.map(d=>d.high),low:hkd.map(d=>d.low),close:hkd.map(d=>d.close),increasing:{{line:{{color:'{RED}'}},fillcolor:'{RED}'}},decreasing:{{line:{{color:'{GREEN}'}},fillcolor:'{GREEN}'}},name:'港股K线'}},
{{type:'bar',x:hvd.map(d=>d.x),y:hvd.map(d=>d.y),marker:{{color:hvd.map(d=>d.color)}},name:'港股成交量',yaxis:'y2'}}
],{{title:'港股 ({h_code})',xaxis:{{rangeslider:{{visible:false}},type:'category'}},yaxis:{{title:'价格(港元)'}},yaxis2:{{title:'成交量',overlaying:'y',side:'right',showgrid:false}},template:'plotly_white',height:400,hovermode:'x unified',legend:{{orientation:'h',y:1.15}}}});
</script></body></html>"""

    with open(panel_file, "w", encoding="utf-8") as f:
        f.write(html)
    return panel_file


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("HTML 分析面板生成 — gen_panels.py v2.0")
    print("=" * 60)

    generated = []

    for name, cfg in STOCKS.items():
        print(f"\n--- {name} ---")

        # A 股单面板 + AH 对比
        a_data = load(name, cfg["a_code"])
        if not a_data:
            print(f"  [{name}] A股数据缺失，跳过")
            continue

        fn = single_panel(name, cfg["a_code"], a_data)
        if fn:
            generated.append(fn)
            print(f"  -> {os.path.basename(fn)}")

        if cfg["has_h"]:
            h_data = load(name, cfg["h_code"])
            if h_data:
                fn = ah_panel(name, cfg["a_code"], cfg["h_code"], a_data, h_data)
                if fn:
                    generated.append(fn)
                    print(f"  -> {os.path.basename(fn)}")
            else:
                print(f"  [{name}] 港股数据缺失，跳过 AH 面板")

    print(f"\n共生成 {len(generated)} 个 HTML 面板")
    for g in generated:
        print(f"  {g}")


if __name__ == "__main__":
    main()
