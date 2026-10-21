# review/probe_rsi_zero.py — CR-005 cycle_05 独立探针（DEC-014）
# 核验零成本口径 A/B/C 的 RSI(5) 回归（output/15_rsi_regression_zero_cost.csv）：
# 1) RSI(5) Wilder 独立重算 + t−1 滞后对齐（反未来函数）；
# 2) 以独立 OLS 实现从日收益明细 CSV 复算 beta/t/p/n 并逐值核对；
# 3) 零成本 C 日收益复利 == 成本谱 (0,0) 行 TotalReturn（跨 BLOCK 锚点）；
# 4) 引擎产物不变性（对 cycle_02 基线 + 各轮已知变更集）。
import hashlib
import json
import math
import os

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF")
OUT = ROOT / "output"
results = []

zc = pd.read_csv(OUT / "15_rsi_regression_zero_cost.csv")
daily = pd.read_csv(OUT / "15_rsi_zero_cost_daily.csv")

# 检查 1：RSI(5) Wilder 独立重算与 t−1 滞后对齐
dl = pd.read_csv(ROOT / "data" / "processed" / "daily_510300.csv", parse_dates=["trade_date"])
close = dl.set_index("trade_date")["close"].sort_index()
dlt = close.diff()
up = dlt.clip(lower=0.0)
dn = -dlt.clip(upper=0.0)
au = up.ewm(alpha=1 / 5, adjust=False, min_periods=5).mean()
ad = dn.ewm(alpha=1 / 5, adjust=False, min_periods=5).mean()
rsi_ind = 100.0 - 100.0 / (1.0 + au / ad)
dates = pd.to_datetime(daily.date)
rsi_on_days = rsi_ind.reindex(dates).to_numpy()          # 当日 RSI
lag_ref = np.concatenate([[np.nan], rsi_on_days[:-1]])   # t−1 收盘 RSI
m = daily.rsi_lag1.notna().to_numpy()
ok1 = bool(np.allclose(daily.rsi_lag1.to_numpy()[m], lag_ref[m], atol=1e-9))
# 反未来函数判别：若误用当日 RSI（不滞后），至少 95% 行会不相等
mismatch = float((daily.rsi_lag1.to_numpy()[m] != rsi_on_days[m]).mean())
results.append((f"RSI 独立重算+t−1 滞后对齐一致（当日误用判别率 {mismatch:.1%}）", ok1 and mismatch > 0.95))


# 检查 2：独立 OLS 复算（numpy lstsq + erfc，独立于 notebook ols_stats 的重新实现）
def ols_ind(y, x):
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    mm = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mm], y[mm]
    n = len(x)
    xm = x - x.mean()
    ym = y - y.mean()
    b1 = float(xm @ ym) / float(xm @ xm)
    b0 = float(y.mean() - b1 * x.mean())
    resid = y - (b0 + b1 * x)
    s2 = float(resid @ resid) / (n - 2)
    se1 = math.sqrt(s2 / float(xm @ xm))
    t1 = b1 / se1
    p1 = math.erfc(abs(t1) / math.sqrt(2.0))
    return b0, b1, t1, p1, n


ok2 = True
for v in ["A", "B", "C"]:
    b0, b1, t1, p1, n1 = ols_ind(daily[f"ret_{v}"] * 1e4, daily.rsi_lag1)
    r = zc[zc.variant == v].iloc[0]
    ok2 &= (abs(b1 - r.beta) < 1e-9 and abs(t1 - r.t_beta) < 1e-9
            and abs(p1 - r.p_beta) < 1e-9 and n1 == int(r.n))
results.append(("独立 OLS 逐值核对 A/B/C（beta/t/p/n <1e-9）", ok2))

# 检查 3：零成本 C 复利 == 成本谱 (0,0) 行（跨 BLOCK 锚点）
cost = pd.read_csv(OUT / "16_cost_sensitivity.csv")
tr00 = float(cost[(cost.commission == 0.0) & (cost.slippage == 0.0)].TotalReturn.iloc[0])
tr_c = float((1.0 + daily.ret_C).prod() - 1.0)
results.append((f"零成本 C 复利 {tr_c:.6f} == 成本谱(0,0) {tr00:.6f}", abs(tr_c - tr00) < 1e-9))

# 检查 4：引擎产物不变性
base = json.load(open(ROOT / "review" / "run_02" / "sha_after.json", encoding="utf-8"))
KNOWN_CHANGED = {f"output\\10_fig{i}{s}" for i, s in
                 [("1", "_concept.png"), ("1", "_data.csv"), ("2", "_case_days.png"),
                  ("2", "_data.csv"), ("4", "_case_20220120.png"), ("4", "_data.csv"),
                  ("5", "_stops_20220120.png")]}
KNOWN_NEW = {"output\\03_noise_bands_1min.csv", "output\\16_cost_w1_zero_slip.csv",
             "output\\15_rsi_regression_zero_cost.csv", "output\\15_rsi_zero_cost_daily.csv"}
changed, new, missing = [], [], []
same = 0
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
ok4 = (set(changed) == KNOWN_CHANGED and set(new) == KNOWN_NEW and not missing
       and tr_ok and same == 82)
results.append((f"不变性: SAME={same} CHANGED=7(已知集) NEW=4(含本轮2个) MISSING={missing} "
                f"trade_record一致={tr_ok}（15_rsi_regression.csv 在 SAME 中）", ok4))

print("=== 探针结果 ===")
allok = True
for r in results:
    print(("PASS" if r[1] else "FAIL"), "-", r[0])
    allok &= bool(r[1])
print()
print(zc[["variant", "alpha_bps", "beta", "t_beta", "p_beta", "n", "r2"]].to_string(index=False))
print("ALL:", "PASS" if allok else "FAIL")
assert allok
