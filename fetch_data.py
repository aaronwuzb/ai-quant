"""
fetch_data.py — 统一股票数据获取脚本 (v2.0)
使用 akshare 获取 L1 基础行情数据，输出标准 JSON + CSV。

数据源:
  A股: akshare.stock_zh_a_daily(adjust='qfq') — Sina 源
 港股: akshare.stock_hk_daily(adjust='qfq') — Sina 源

单位转换:
  A股 volume: 股 → 手 (/100)
  港股 volume: 股 (不变)
  amount: 元 / 港元 (不变)

输出: {股票简称}_{代码标识}_近一年数据.{json,csv}
"""

import akshare as ak
import json, os, csv, sys
from datetime import datetime

# ============================================================
# 配置
# ============================================================
DATE_START = "2025-07-04"
DATE_END   = "2026-07-04"

STOCKS = [
    {
        "name": "中芯国际",
        "a_symbol": "sh688981",
        "a_code":   "sh688981",
        "h_symbol": "00981",
        "h_code":   "hk00981",
        "has_h":    True,
        "tags":     ["半导体龙头", "AH双重上市", "晶圆代工"],
    },
    {
        "name": "比亚迪",
        "a_symbol": "sz002594",
        "a_code":   "sz002594",
        "h_symbol": "01211",
        "h_code":   "hk01211",
        "has_h":    True,
        "tags":     ["新能源龙头", "AH双重上市", "高成长"],
    },
    {
        "name": "长江电力",
        "a_symbol": "sh600900",
        "a_code":   "sh600900",
        "h_symbol": None,
        "h_code":   None,
        "has_h":    False,
        "tags":     ["高股息", "蓝筹", "防御型", "纯A股"],
    },
]

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 数据获取
# ============================================================

def fetch_a_share(symbol: str, name: str) -> list[dict]:
    """
    获取 A 股日线数据 (前复权)
    数据源: akshare.stock_zh_a_daily (Sina)
    单位转换: volume 股→手 (/100)
    """
    print(f"  [{name}] 获取 A 股 {symbol} ...", end=" ", flush=True)
    try:
        df = ak.stock_zh_a_daily(symbol=symbol, adjust="qfq")
    except Exception as e:
        print(f"失败: {e}")
        return []

    print(f"获取 {len(df)} 条全量记录", end="", flush=True)

    records = []
    for _, row in df.iterrows():
        d = str(row["date"])
        if d < DATE_START or d > DATE_END:
            continue
        records.append({
            "date":   d,
            "open":   round(float(row["open"]),   2),
            "close":  round(float(row["close"]),  2),
            "high":   round(float(row["high"]),   2),
            "low":    round(float(row["low"]),    2),
            "volume": int(row["volume"] / 100),        # 股 → 手
            "amount": round(float(row["amount"]), 2),  # 元, 不变
        })

    records.sort(key=lambda x: x["date"])
    print(f" -> 筛选出 {len(records)} 条 ({DATE_START}~{DATE_END})")
    return records


def fetch_hk_share(symbol: str, name: str) -> list[dict]:
    """
    获取港股日线数据 (前复权)
    数据源: akshare.stock_hk_daily (Sina)
    单位: volume 股, amount 港元 (均不变)
    """
    print(f"  [{name}] 获取港股 {symbol} ...", end=" ", flush=True)
    try:
        df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
    except Exception as e:
        print(f"失败: {e}")
        return []

    print(f"获取 {len(df)} 条全量记录", end="", flush=True)

    records = []
    for _, row in df.iterrows():
        d = str(row["date"])
        if d < DATE_START or d > DATE_END:
            continue
        records.append({
            "date":   d,
            "open":   round(float(row["open"]),   2),
            "close":  round(float(row["close"]),  2),
            "high":   round(float(row["high"]),   2),
            "low":    round(float(row["low"]),    2),
            "volume": int(row["volume"]),               # 股, 不变
            "amount": round(float(row["amount"]), 2),  # 港元, 不变
        })

    records.sort(key=lambda x: x["date"])
    print(f" -> 筛选出 {len(records)} 条 ({DATE_START}~{DATE_END})")
    return records


# ============================================================
# 输出
# ============================================================

def save_json(name: str, code: str, data: list[dict], source: str) -> str:
    """保存 JSON 文件，含元信息"""
    fname = f"{name}_{code}_近一年数据.json"
    path  = os.path.join(OUTPUT_DIR, fname)

    wrapper = {
        "_meta": {
            "stock": name,
            "code":  code,
            "source": source,
            "fetch_time": datetime.now().isoformat(),
            "date_range": [data[0]["date"], data[-1]["date"]] if data else [],
            "total_days": len(data),
            "adjust": "qfq",
        },
        "data": data,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=2)
    return fname


def save_csv(name: str, code: str, data: list[dict]) -> str:
    """保存 CSV 文件"""
    fname = f"{name}_{code}_近一年数据.csv"
    path  = os.path.join(OUTPUT_DIR, fname)

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "close", "high", "low", "volume", "amount"])
        for d in data:
            w.writerow([d["date"], d["open"], d["close"], d["high"], d["low"],
                        d["volume"], d["amount"]])
    return fname


def save(data: list[dict], name: str, code: str, source: str) -> dict:
    """保存 JSON + CSV，返回统计"""
    if not data:
        print(f"  [{name}] {code}: 无数据，跳过")
        return {}
    jf = save_json(name, code, data, source)
    cf = save_csv(name, code, data)
    return {
        "name": name, "code": code,
        "days": len(data),
        "range": f"{data[0]['date']}~{data[-1]['date']}",
        "json": jf, "csv": cf,
        "close_start": data[0]["close"],
        "close_end":   data[-1]["close"],
    }


# ============================================================
# 质量检查 (基础)
# ============================================================

def quick_qc(data: list[dict], name: str, code: str):
    """快速基础质量检查"""
    if not data:
        return
    issues = []
    n = len(data)

    # 价格逻辑
    for i, d in enumerate(data):
        if not (d["low"] <= d["open"]  <= d["high"] and
                d["low"] <= d["close"] <= d["high"]):
            issues.append(f"[{d['date']}] 价格逻辑异常: O={d['open']} C={d['close']} "
                          f"H={d['high']} L={d['low']}")
        if d["volume"] < 0:
            issues.append(f"[{d['date']}] 成交量负值: {d['volume']}")
        if d["amount"] < 0:
            issues.append(f"[{d['date']}] 成交额负值: {d['amount']}")

    # 价格跳空检测 (>15%)
    for i in range(1, n):
        prev_c = data[i-1]["close"]
        curr_o = data[i]["open"]
        if prev_c and abs((curr_o - prev_c) / prev_c) > 0.15:
            issues.append(f"[{data[i]['date']}] 价格跳空: prev_close={prev_c:.2f} "
                          f"open={curr_o:.2f} ({(curr_o-prev_c)/prev_c*100:+.1f}%)")

    if issues:
        print(f"  [{name}] {code} QC 警报 ({len(issues)} 项):")
        for iss in issues[:5]:
            print(f"    - {iss}")
    else:
        print(f"  [{name}] {code} QC 通过 ✓")

    return issues


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("股票数据获取 — fetch_data.py v2.0")
    print(f"日期范围: {DATE_START} ~ {DATE_END}")
    print(f"数据源: akshare (Sina)")
    print("=" * 60)

    results = []

    for stk in STOCKS:
        name = stk["name"]
        print(f"\n--- {name} ---")

        # A 股
        a_data = fetch_a_share(stk["a_symbol"], name)
        quick_qc(a_data, name, stk["a_code"])
        r = save(a_data, name, stk["a_code"], "akshare.stock_zh_a_daily")
        if r:
            results.append(r)

        # 港股
        if stk["has_h"]:
            h_data = fetch_hk_share(stk["h_symbol"], name)
            quick_qc(h_data, name, stk["h_code"])
            r = save(h_data, name, stk["h_code"], "akshare.stock_hk_daily")
            if r:
                results.append(r)

    # 汇总
    print("\n" + "=" * 60)
    print("数据获取完成！汇总:")
    print(f"{'股票':<10} {'代码':<12} {'天数':<6} {'日期范围':<26} {'起始价':>10} {'最新价':>10} {'涨跌幅':>8}")
    print("-" * 92)
    for r in results:
        chg = (r["close_end"] - r["close_start"]) / r["close_start"] * 100 if r["close_start"] else 0
        print(f"{r['name']:<10} {r['code']:<12} {r['days']:<6} {r['range']:<26} "
              f"{r['close_start']:>10.2f} {r['close_end']:>10.2f} {chg:>+7.2f}%")

    print(f"\n共 {len(results)} 个数据文件")
    return results


if __name__ == "__main__":
    main()
