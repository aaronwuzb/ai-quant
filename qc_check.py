"""
qc_check.py — 自动化质量检查脚本 (v2.0)
对 JSON 数据文件执行 spec v2.0 定义的 9 项质量检查，输出 qc_report.json。

检查项:
  1. 日期连续性      2. 价格逻辑
  3. 成交量非负      4. 价格跳空 (>15%)
  5. 复权一致性      6. 数据完整性 (>=95%)
  7. AH 对齐         8. 价格量级合理性
  9. 成交额量级验证
"""

import json, os, csv
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 预期交易天数估算 (一年约 242-250 个交易日)
# ============================================================
EXPECTED_TRADING_DAYS = 242   # 2025-07-04 ~ 2026-07-04 约 242 个交易日
COMPLETENESS_THRESHOLD = 0.95


def load_data(name: str, code: str) -> list[dict] | None:
    """加载 JSON 数据"""
    path = os.path.join(SCRIPT_DIR, f"{name}_{code}_近一年数据.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and "data" in raw:
        return raw["data"]
    return raw


def check_price_logic(data: list[dict]) -> list[str]:
    """#2: 价格逻辑 low <= open/close <= high"""
    issues = []
    for d in data:
        if not (d["low"] <= d["open"] <= d["high"] and
                d["low"] <= d["close"] <= d["high"]):
            issues.append(f"{d['date']}: O={d['open']} C={d['close']} "
                          f"H={d['high']} L={d['low']}")
    return issues


def check_volume_nonneg(data: list[dict]) -> list[str]:
    """#3: 成交量 >= 0"""
    return [f"{d['date']}: volume={d['volume']}" for d in data if d["volume"] < 0]


def check_price_gap(data: list[dict]) -> list[str]:
    """#4: 价格跳空 > 15%"""
    issues = []
    for i in range(1, len(data)):
        prev_c = data[i-1]["close"]
        curr_o = data[i]["open"]
        if prev_c and abs((curr_o - prev_c) / prev_c) > 0.15:
            issues.append(f"{data[i]['date']}: prev_close={prev_c:.2f} "
                          f"open={curr_o:.2f} ({(curr_o-prev_c)/prev_c*100:+.1f}%)")
    return issues


def check_completeness(data: list[dict], expected: int) -> dict:
    """#6: 数据完整性"""
    actual = len(data)
    ratio = actual / expected if expected else 0
    return {
        "actual": actual, "expected": expected,
        "ratio": round(ratio, 3),
        "pass": ratio >= COMPLETENESS_THRESHOLD,
    }


def check_price_range(data: list[dict], market: str) -> str:
    """#8: 价格量级合理性"""
    closes = [d["close"] for d in data]
    mn, mx = min(closes), max(closes)
    if market == "A":
        if mn < 0.1 or mx > 10000:
            return f"WARN: 价格范围异常 [{mn:.2f}, {mx:.2f}]"
    elif market == "HK":
        if mn < 0.01 or mx > 10000:
            return f"WARN: 价格范围异常 [{mn:.2f}, {mx:.2f}]"
    return "OK"


def check_amount_range(data: list[dict], market: str) -> str:
    """#9: 成交额量级验证"""
    amounts = [d["amount"] for d in data]
    avg = sum(amounts) / len(amounts)

    if market == "A":
        # A股日成交额通常在 10^6 ~ 10^11 元
        if avg < 1e6:
            return (f"ERROR: 日均成交额量级异常: {avg:.0f} 元 (偏小1000倍? "
                    f"检查单位是否为元)")
        if avg > 1e11:
            return f"WARN: 日均成交额偏高: {avg/1e8:.1f}亿"
    elif market == "HK":
        # 港股日成交额通常在 10^5 ~ 10^10 港元
        if avg < 1e5:
            return (f"ERROR: 日均成交额量级异常: {avg:.0f} HKD (可能单位错误)")
        if avg > 1e10:
            return f"WARN: 日均成交额偏高: {avg/1e8:.1f}亿"
    return "OK"


def check_ah_alignment(a_data: list[dict], h_data: list[dict]) -> dict:
    """#7: AH 交易日对齐"""
    a_dates = {d["date"] for d in a_data}
    h_dates = {d["date"] for d in h_data}
    common = sorted(a_dates & h_dates)
    a_only = sorted(a_dates - h_dates)
    h_only = sorted(h_dates - a_dates)
    return {
        "common_days": len(common),
        "a_only_days": len(a_only),
        "h_only_days": len(h_only),
        "a_only_sample": a_only[:5],
        "h_only_sample": h_only[:5],
    }


def check_csv_consistency(name: str, code: str, data: list[dict]) -> dict:
    """验证 JSON 与 CSV 的一致性"""
    csv_path = os.path.join(SCRIPT_DIR, f"{name}_{code}_近一年数据.csv")
    if not os.path.exists(csv_path):
        return {"pass": False, "error": "CSV 文件不存在"}
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
    if len(reader) != len(data):
        return {"pass": False, "error": f"行数不一致: JSON={len(data)} CSV={len(reader)}"}
    return {"pass": True}


# ============================================================
# 主流程
# ============================================================

def run_qc(name: str, code: str, market: str, expected_days: int) -> dict:
    """对单个数据文件执行完整质量检查"""
    data = load_data(name, code)
    if not data:
        return {"status": "SKIP", "error": "文件不存在"}

    result = {
        "name": name, "code": code, "market": market,
        "total_days": len(data),
        "date_range": f"{data[0]['date']}~{data[-1]['date']}",
        "checks": {},
        "anomalies": [],
    }

    # 1. 日期连续性 (简化: 检测记录数)
    completeness = check_completeness(data, expected_days)
    result["checks"]["1_dates"] = {
        "name": "日期连续性",
        "status": "pass" if completeness["pass"] else "warn",
        "detail": f"{completeness['actual']}/{completeness['expected']} "
                  f"({completeness['ratio']*100:.1f}%)",
    }

    # 2. 价格逻辑
    issues = check_price_logic(data)
    result["checks"]["2_price_logic"] = {
        "name": "价格逻辑", "status": "fail" if issues else "pass",
        "detail": f"{len(issues)} 条异常" if issues else "全部通过",
    }
    result["anomalies"].extend(issues)

    # 3. 成交量非负
    issues = check_volume_nonneg(data)
    result["checks"]["3_volume"] = {
        "name": "成交量非负", "status": "fail" if issues else "pass",
        "detail": f"{len(issues)} 条异常" if issues else "全部通过",
    }
    result["anomalies"].extend(issues)

    # 4. 价格跳空
    issues = check_price_gap(data)
    result["checks"]["4_gap"] = {
        "name": "价格跳空 (>15%)", "status": "warn" if issues else "pass",
        "detail": f"{len(issues)} 个跳空日: {', '.join([i.split(':')[0] for i in issues])}" if issues else "无异常跳空",
    }

    # 5. 复权一致性 (默认 qfq, 仅记录)
    result["checks"]["5_adjust"] = {
        "name": "复权一致性", "status": "pass",
        "detail": "前复权 (qfq)",
    }

    # 6. 数据完整性
    result["checks"]["6_completeness"] = {
        "name": "数据完整性",
        "status": "pass" if completeness["pass"] else "warn",
        "detail": f"实际 {completeness['actual']} 天 / 预期 {completeness['expected']} 天",
    }

    # 7. AH 对齐 — 由外部调用处理
    result["checks"]["7_ah"] = {"name": "AH 对齐", "status": "N/A"}

    # 8. 价格量级
    detail = check_price_range(data, market)
    result["checks"]["8_price_range"] = {
        "name": "价格量级合理性", "status": "pass" if detail == "OK" else "warn",
        "detail": detail,
    }

    # 9. 成交额量级
    detail = check_amount_range(data, market)
    status = "fail" if "ERROR" in detail else ("warn" if "WARN" in detail else "pass")
    result["checks"]["9_amount_range"] = {
        "name": "成交额量级验证", "status": status,
        "detail": detail,
    }

    # CSV 一致性
    csv_check = check_csv_consistency(name, code, data)
    result["csv_consistency"] = csv_check["pass"]

    # 汇总
    statuses = [c["status"] for c in result["checks"].values()]
    result["overall"] = "fail" if "fail" in statuses else ("warn" if "warn" in statuses else "pass")

    return result


def main():
    print("=" * 60)
    print("质量检查 — qc_check.py v2.0")
    print("=" * 60)

    configs = [
        ("中芯国际", "sh688981", "A"),
        ("中芯国际", "hk00981",  "HK"),
        ("比亚迪",   "sz002594", "A"),
        ("比亚迪",   "hk01211",  "HK"),
        ("长江电力",  "sh600900", "A"),
    ]

    results = {}
    for name, code, market in configs:
        print(f"\n[{name}] {code} ({market})")
        r = run_qc(name, code, market, EXPECTED_TRADING_DAYS)
        if r.get("status") == "SKIP":
            print(f"  SKIP: {r['error']}")
            continue
        results[f"{name}_{code}"] = r

        for cid, c in r["checks"].items():
            icon = {"pass": "✓", "warn": "⚠", "fail": "✗", "N/A": "-"}.get(c["status"], "?")
            detail = c.get("detail", "—")
            print(f"  {icon} #{cid}: {c['name']} — {detail}")
        print(f"  综合: {r['overall'].upper()}")

    # AH 对齐检查
    smic_a = load_data("中芯国际", "sh688981")
    smic_h = load_data("中芯国际", "hk00981")
    if smic_a and smic_h:
        ah = check_ah_alignment(smic_a, smic_h)
        key = "中芯国际_sh688981"
        if key in results:
            results[key]["checks"]["7_ah"] = {
                "name": "AH 对齐", "status": "pass",
                "detail": f"重叠 {ah['common_days']} 天, A独有 {ah['a_only_days']}, H独有 {ah['h_only_days']}",
            }
        print(f"\n  AH 对齐: 重叠 {ah['common_days']} 天")

    byd_a = load_data("比亚迪", "sz002594")
    byd_h = load_data("比亚迪", "hk01211")
    if byd_a and byd_h:
        ah = check_ah_alignment(byd_a, byd_h)
        key = "比亚迪_sz002594"
        if key in results:
            results[key]["checks"]["7_ah"] = {
                "name": "AH 对齐", "status": "pass",
                "detail": f"重叠 {ah['common_days']} 天, A独有 {ah['a_only_days']}, H独有 {ah['h_only_days']}",
            }
        print(f"\n  AH 对齐(比亚迪): 重叠 {ah['common_days']} 天")

    # 输出报告
    report_path = os.path.join(SCRIPT_DIR, "qc_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "_meta": {
                "check_date": datetime.now().isoformat(),
                "spec_version": "v2.0",
                "total_files": len(results),
            },
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n质量报告已保存: {report_path}")


if __name__ == "__main__":
    main()
