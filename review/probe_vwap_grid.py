# review/probe_vwap_grid.py — CR-002 cycle_02 独立探针
# 独立于 notebook 的第三代码路径：直读 data/processed 分钟 parquet，
# 复算网格口径 VWAP 并与 output/grids/<g>/04_vwap_check.csv 核对；
# 专项验证 13:00=11:30 语义、午休跳过、零成交 bar、缺竞价 bar 日、未来函数边界。
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF")
PROC = ROOT / "data" / "processed"
OUT = ROOT / "output"

mn = pd.read_parquet(PROC / "minute_bars_510300.parquet")
mn = mn[(mn.trade_date >= "2017-01-01") & (mn.trade_date <= "2025-12-31")].sort_values("trade_time")
days = sorted(mn.trade_date.unique())


def lk(s):
    return int(s[:2]) * 60 + int(s[3:])


LABELS = sorted(mn.hhmm.unique(), key=lk)
IDX = {s: i for i, s in enumerate(LABELS)}


def make_grid(step, last_pm):
    am, pm = [], []
    t = 10 * 60
    while t <= 11 * 60:
        am.append(f"{t // 60:02d}:{t % 60:02d}")
        t += step
    t = 13 * 60
    end = lk(last_pm)
    while t <= end:
        pm.append(f"{t // 60:02d}:{t % 60:02d}")
        t += step
    return am + pm


GRIDS = {"g30": make_grid(30, "14:30"), "g15": make_grid(15, "14:45"), "g05": make_grid(5, "14:55")}
SIG_BAR = {"13:00": "11:30"}

# 矩阵化（独立实现）
C = mn.pivot(index="trade_date", columns="hhmm", values="close").reindex(index=days, columns=LABELS).to_numpy(float)
V = mn.pivot(index="trade_date", columns="hhmm", values="vol").reindex(index=days, columns=LABELS).to_numpy(float)
day_idx = {d: i for i, d in enumerate(days)}


def grid_bar_cols(g):
    sigs = [SIG_BAR.get(t, t) for t in GRIDS[g]] + ["15:00"]
    out, c0 = [], 0
    for s in sigs:
        c1 = IDX[s]
        out.append((s, c0, c1))
        c0 = c1 + 1
    return out


def vwap_at(di, g, tau, upto_offset=0):
    """独立复算 VWAP_g(tau)；upto_offset>0 时多计入 offset 列（未来函数敏感性测试用）。"""
    slab = SIG_BAR.get(tau, tau)
    num = den = 0.0
    for s, c0, c1 in grid_bar_cols(g):
        end = c1 + upto_offset if s == slab else c1
        vol_b = np.nansum(V[di, c0:end + 1])
        cl = C[di, end]
        if not np.isnan(cl):
            num += cl * vol_b
            den += vol_b
        if s == slab:
            break
    return num / den if den > 0 else np.nan


results = {"checks": [], "failures": []}


def check(name, ok, detail=""):
    results["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    if not ok:
        results["failures"].append({"name": name, "detail": detail})


# 1) 与 notebook 导出的抽检文件逐值核对（第三路径 vs 产物）
n_cmp = 0
for g in GRIDS:
    ref = pd.read_csv(OUT / "grids" / g / "04_vwap_check.csv")
    bad = 0
    for r in ref.itertuples():
        di = day_idx[pd.Timestamp(r.date)]
        mine = vwap_at(di, g, r.tau)
        if abs(mine - r.vwap) > 1e-9:
            bad += 1
    n_cmp += len(ref)
    check(f"vwaph_csv_match_{g}", bad == 0, f"{len(ref)} rows, mismatches={bad}")

# 2) 13:00=11:30 语义：VWAP(13:00) 不得含 13:01..13:30 的 bar
d_test = day_idx[pd.Timestamp("2022-09-15")]
v_1300 = vwap_at(d_test, "g30", "13:00")
v_1130 = vwap_at(d_test, "g30", "11:00")  # g30 无 11:30 决策点，直接手工算到 11:30
# 手工算到 11:30（独立路径：直接取列区间）
c1_1130 = IDX["11:30"]
num = np.nansum(C[d_test, :c1_1130 + 1][[IDX[s] for s in ["10:00", "10:30", "11:00"]]] * 0)  # 占位不用
num = den = 0.0
for s, c0, c1 in grid_bar_cols("g30"):
    vol_b = np.nansum(V[d_test, c0:c1 + 1])
    num += C[d_test, c1] * vol_b
    den += vol_b
    if s == "11:30":
        break
manual_1130 = num / den
check("tau1300_uses_1130bar", abs(v_1300 - manual_1130) < 1e-12,
      f"vwap(13:00)={v_1300:.6f} vs manual-to-11:30={manual_1130:.6f}")
# 且应不同于错误包含 13:01..13:30 的值
c1_1330 = IDX["13:30"]
num2 = den2 = 0.0
for s, c0, c1 in grid_bar_cols("g30"):
    if s == "11:30":
        vol_b = np.nansum(V[d_test, c0:c1_1330 + 1])
        num2 += C[d_test, c1_1330] * vol_b
        den2 += vol_b
        break
    vol_b = np.nansum(V[d_test, c0:c1 + 1])
    num2 += C[d_test, c1] * vol_b
    den2 += vol_b
wrong_with_pm = num2 / den2
check("tau1300_excludes_afternoon", abs(v_1300 - wrong_with_pm) > 1e-6,
      f"correct={v_1300:.6f} wrong_incl_1330={wrong_with_pm:.6f}")

# 3) 午休跳过：11:30 与 13:01 之间不存在标签（构造层面）
gap = [s for s in LABELS if lk("11:30") < lk(s) < lk("13:01")]
check("lunch_labels_absent", gap == [], f"labels between 11:30 and 13:01: {gap}")

# 4) 零成交 bar（2024-09-27 上交所故障 6 根）不产生增量：
# 将当日全部零成交列整体剔除后重算 VWAP，所有 g05 决策点值必须与原值一致
d_f = day_idx[pd.Timestamp("2024-09-27")]
zero_cols = sorted(i for i in range(1, len(LABELS)) if (np.isnan(V[d_f, i]) or V[d_f, i] == 0))
V_alt = V.copy()
C_alt = C.copy()
V_alt[d_f, zero_cols] = np.nan      # 等价于“不存在这些 bar”：NaN 与 0 都不应产生增量
def vwap_at_mats(di, g, tau, Cm, Vm):
    slab = SIG_BAR.get(tau, tau)
    num = den = 0.0
    for s, c0, c1 in grid_bar_cols(g):
        vol_b = np.nansum(Vm[di, c0:c1 + 1])
        cl = Cm[di, c1]
        if not np.isnan(cl):
            num += cl * vol_b
            den += vol_b
        if s == slab:
            break
    return num / den if den > 0 else np.nan
diffs = [abs(vwap_at_mats(d_f, "g05", t, C, V) - vwap_at_mats(d_f, "g05", t, C_alt, V_alt))
         for t in GRIDS["g05"]]
check("zero_vol_no_increment_20240927", zero_cols and max(diffs) < 1e-9,
      f"zero_cols={len(zero_cols)} max_diff_with_bars_removed={max(diffs):.2e}")

# 5) 2017-08-09 缺竞价 bar：全决策点 VWAP 有限
d_i = day_idx[pd.Timestamp("2017-08-09")]
all_finite = all(not np.isnan(vwap_at(d_i, g, t)) for g in GRIDS for t in GRIDS[g])
check("incomplete_day_20170809_finite", all_finite, "")

# 6) 未来函数边界：对“额外列有正成交且其收盘 ≠ 当前 VWAP”的 (d,τ)，含 τ 后一列必须得到不同值
# （若额外列收盘恰等于当前 VWAP，加入后比例不变，属数学恒等，不构成判别力）
rng = np.random.RandomState(7)
diff_found = 0
total = 0
skipped_zero = 0
skipped_degenerate = 0
for di in rng.choice(len(days), 10, replace=False):
    for tau in GRIDS["g30"]:
        slab = SIG_BAR.get(tau, tau)
        nxt = IDX[slab] + 1
        vn = V[di, nxt]
        if np.isnan(vn) or vn == 0 or np.isnan(C[di, nxt]):
            skipped_zero += 1
            continue
        a = vwap_at(di, "g30", tau)
        if abs(a - C[di, nxt]) <= 1e-9:
            skipped_degenerate += 1
            continue
        b = vwap_at(di, "g30", tau, upto_offset=1)
        total += 1
        if abs(a - b) > 1e-12:
            diff_found += 1
check("lookahead_boundary_sensitive", total > 0 and diff_found == total,
      f"{diff_found}/{total} informative cases change; skipped: zero-vol={skipped_zero} degenerate(close==vwap)={skipped_degenerate}")

# 7) 止损行为抽查：B-g30 随机 5 笔止损平仓（排除 15:00 强平 EOD），独立复算 stop 一致性
O = mn.pivot(index="trade_date", columns="hhmm", values="open").reindex(index=days, columns=LABELS).to_numpy(float)
def day_open_of(di):
    if not np.isnan(O[di, IDX["09:30"]]):
        return O[di, IDX["09:30"]]
    return O[di, np.argmax(~np.isnan(O[di]))]      # 2017-08-09 缺竞价 bar → 首根有效 bar 开盘

tr = pd.read_csv(OUT / "grids" / "g30" / "06_bandvwap_trades.csv")
dly = pd.read_csv(PROC / "daily_510300.csv", parse_dates=["trade_date"]).sort_values("trade_date")
dly["ret"] = dly["pct_chg"] / 100.0
pc_map = dict(zip(dly.trade_date.dt.strftime("%Y-%m-%d"), dly["pre_close"]))
DO = np.array([day_open_of(di) for di in range(len(days))])
MOVE = np.abs(C[:, 1:] / DO[:, None] - 1.0)
SIGMA14 = pd.DataFrame(MOVE).rolling(14).mean().shift(1).to_numpy()
PL = LABELS[1:]
PP = {s: i for i, s in enumerate(PL)}
closes = tr[tr.action.isin(["CLOSE_LONG", "CLOSE_SHORT"]) & (tr.reason != "EOD")]
samp = closes.sample(5, random_state=11)
stop_ok = 0
for r in samp.itertuples():
    dstr = pd.Timestamp(r.date).strftime("%Y-%m-%d")
    di = day_idx[pd.Timestamp(r.date)]
    slab = SIG_BAR.get(r.decision_time, r.decision_time)
    sc = IDX[slab]
    sg = SIGMA14[di, PP[slab]]
    ub = max(DO[di], pc_map[dstr]) * (1 + sg)
    lb = min(DO[di], pc_map[dstr]) * (1 - sg)
    vw = vwap_at(di, "g30", r.decision_time)
    p = C[di, sc]
    if r.action == "CLOSE_LONG":
        ok = p < max(ub, vw) - 1e-12
    else:
        ok = p > min(lb, vw) + 1e-12
    stop_ok += int(ok)
check("stop_recalc_5cases", stop_ok == 5, f"{stop_ok}/5 stop-trigger exits verified (EOD excluded)")

print(json.dumps({"n_value_comparisons": n_cmp,
                  "n_checks": len(results["checks"]),
                  "n_failures": len(results["failures"])}, ensure_ascii=False))
for c in results["checks"]:
    print(("PASS " if c["ok"] else "FAIL "), c["name"], "|", c["detail"])
sys.exit(1 if results["failures"] else 0)
