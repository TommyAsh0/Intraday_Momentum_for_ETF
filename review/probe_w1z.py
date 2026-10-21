# review/probe_w1z.py — CR-004 cycle_04 独立探针（DEC-013）
# 核验三变体零滑点万1对照表（output/16_cost_w1_zero_slip.csv）：
# 1) C 行与成本谱 (万1,0tick) 行一致；2) 滑点增量量级勾稽（对比 grids 成交明细）；
# 3) 执行行数勾稽；4) 引擎产物不变性（对 cycle_02 基线 + CD-003 有意变更集）。
import hashlib
import json
import os

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF")
OUT = ROOT / "output"
results = []

w1z = pd.read_csv(OUT / "16_cost_w1_zero_slip.csv")
cost = pd.read_csv(OUT / "16_cost_sensitivity.csv")

# 检查 1：口径与 C 行勾稽
ok1a = bool((w1z.commission.round(6) == 0.0001).all() and (w1z.slippage == 0.0).all())
c_w = w1z[w1z.Variant == "C"].iloc[0]
c_s = cost[(cost.commission.round(6) == 0.0001) & (cost.slippage == 0.0)].iloc[0]
ok1b = abs(c_w.TotalReturn - c_s.TotalReturn) < 1e-9 and abs(c_w.Sharpe - c_s.Sharpe) < 1e-9
results.append(("口径=万1/0tick 且 C 行==成本谱同行", ok1a and ok1b))

# 检查 2：执行行数勾稽（grids\g30 成交明细：A 2 笔/趟、B/C 2 笔/趟）
trA = pd.read_csv(OUT / "grids" / "g30" / "05_oppband_trades.csv")
trB = pd.read_csv(OUT / "grids" / "g30" / "06_bandvwap_trades.csv")
ok2 = (int(w1z[w1z.Variant == "A"].exec_rows.iloc[0]) == len(trA)
       and int(w1z[w1z.Variant == "B"].exec_rows.iloc[0]) == len(trB)
       and int(w1z[w1z.Variant == "C"].exec_rows.iloc[0]) == len(trB))
results.append((f"exec_rows 勾稽 A={len(trA)} B/C={len(trB)}", ok2))

# 检查 3：滑点增量量级勾稽
# 移除 1 tick 滑点的期末 AUM 增量 ≈ Σ(每腿 shares×0.001) 的复利累积，应与 Σ 同量级且略大
base_end = {"A": 1222781.49, "B": 1e6 * (1 - 0.188985)}  # cycle_02 不变性记录 / 08 汇总
sum08 = pd.read_csv(OUT / "08_summary_stats.csv")
for v, tr in [("A", trA), ("B", trB)]:
    row08 = sum08[(sum08.Variant == v) & (sum08.Grid == "g30")].iloc[0]
    base_end[v] = 1e6 * (1.0 + float(row08["TotalReturn"]))
ok3 = True
detail = []
for v, tr in [("A", trA), ("B", trB)]:
    slip_sum = float((tr["shares"] * 0.001).sum())
    new_end = 1e6 * (1.0 + float(w1z[w1z.Variant == v].TotalReturn.iloc[0]))
    delta = new_end - base_end[v]
    ratio = delta / slip_sum
    detail.append((v, round(slip_sum, 0), round(delta, 0), round(ratio, 2)))
    ok3 &= 0.5 < ratio < 3.0 and delta > 0
results.append(("滑点增量量级(Δ/Σslip∈(0.5,3)且Δ>0)", ok3, detail))

# 检查 4：引擎产物不变性（对 cycle_02 基线；允许 CD-003 已知 7 变更 + 2 新增）
base = json.load(open(ROOT / "review" / "run_02" / "sha_after.json", encoding="utf-8"))
KNOWN_CHANGED = {f"output\\10_fig{i}{s}" for i, s in
                 [("1", "_concept.png"), ("1", "_data.csv"), ("2", "_case_days.png"),
                  ("2", "_data.csv"), ("4", "_case_20220120.png"), ("4", "_data.csv"),
                  ("5", "_stops_20220120.png")]}
KNOWN_NEW = {"output\\03_noise_bands_1min.csv", "output\\16_cost_w1_zero_slip.csv"}
changed, same, new, missing = [], 0, [], []
for dirpath, _, files in os.walk(OUT):
    for fn in files:
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
        if "ext" in rel:
            continue
        h = hashlib.sha256(open(os.path.join(dirpath, fn), "rb").read()).hexdigest()
        if rel in base:
            if base[rel] == h:
                same += 1
            else:
                changed.append(rel)
        else:
            new.append(rel)
missing = [k for k in base if k != "trade_record.csv" and not (ROOT / k).exists()]
tr_ok = base["trade_record.csv"] == hashlib.sha256(open(ROOT / "trade_record.csv", "rb").read()).hexdigest()
ok4 = (set(changed) == KNOWN_CHANGED and set(new) == KNOWN_NEW and not missing and tr_ok
       and same == 82)
results.append((f"不变性: SAME={same} CHANGED={len(changed)}(=CD-003已知集) NEW={sorted(new)} "
                f"MISSING={missing} trade_record一致={tr_ok}", ok4))

print("=== 探针结果 ===")
allok = True
for r in results:
    print(("PASS" if r[1] else "FAIL"), "-", r[0])
    if len(r) > 2:
        for row in r[2]:
            print("     ", row)
    allok &= bool(r[1])
print("ALL:", "PASS" if allok else "FAIL")
assert allok
