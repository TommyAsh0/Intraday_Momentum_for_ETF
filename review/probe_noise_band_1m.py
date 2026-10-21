# review/probe_noise_band_1m.py — CR-003 cycle_03 独立探针（DEC-012）
# 独立于 notebook 的第三代码路径：直读 data/processed 分钟 parquet + 日线 csv，
# 复算 move/σ/UB/LB 并与 output/03_noise_bands_1min.csv 及图数据 CSV 逐值核对；
# 专项验证：1 分钟分辨率（非检查点步进）、检查点值与引擎决策值一致、反未来函数。
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF")
OUT = ROOT / "output"
LOOKBACK = 14

mn = pd.read_parquet(ROOT / "data" / "processed" / "minute_bars_510300.parquet")
mn = mn[(mn.trade_date >= "2017-01-01") & (mn.trade_date <= "2025-12-31")].sort_values("trade_time")
dl = pd.read_csv(ROOT / "data" / "processed" / "daily_510300.csv", parse_dates=["trade_date"])
pc_map = dict(zip(dl.trade_date.dt.strftime("%Y-%m-%d"), dl.pre_close))


def lk(s):
    return int(s[:2]) * 60 + int(s[3:])


LABELS = sorted(mn.hhmm.unique(), key=lk)
PLAB = [s for s in LABELS if s != "09:30"]
assert len(LABELS) == 241 and len(PLAB) == 240
days = sorted(mn.trade_date.dt.strftime("%Y-%m-%d").unique())
n_days = len(days)

C = mn.pivot_table(index="trade_date", columns="hhmm", values="close")
C.index = C.index.strftime("%Y-%m-%d")
O = mn.pivot_table(index="trade_date", columns="hhmm", values="open")
O.index = O.index.strftime("%Y-%m-%d")
Cv = C.reindex(days)[LABELS].to_numpy()
Ov = O.reindex(days)[LABELS].to_numpy()
i0930 = LABELS.index("09:30")
first_valid = np.argmax(~np.isnan(Ov), axis=1)
day_open = np.where(np.isnan(Ov[:, i0930]), Ov[np.arange(n_days), first_valid], Ov[:, i0930])
pre_close = np.array([pc_map[d] for d in days])
MOVE = np.abs(Cv[:, 1:] / day_open[:, None] - 1.0)

csv = pd.read_csv(OUT / "03_noise_bands_1min.csv")
assert len(csv) == n_days * 240, f"行数 {len(csv)} != {n_days * 240}"
assert csv.price_label.tolist() == PLAB * n_days, "price_label 顺序不符"
assert csv.date.tolist() == [d for d in days for _ in range(240)], "date 顺序不符"

results = []

# 检查 1：前 14 个样本日 σ 全 NaN（无带不交易）
head_nan = csv.iloc[: LOOKBACK * 240][["sigma", "UB", "LB"]].isna().all().all()
results.append(("前14日σ/UB/LB全NaN", bool(head_nan)))

# 检查 2：随机 24 个 (d,τ) 独立复算（mean 仅含 t-14..t-1 → 反未来函数由构造保证）
rng = np.random.default_rng(20261005)
ok2 = 0
worst = 0.0
for _ in range(24):
    di = int(rng.integers(LOOKBACK, n_days))
    li = int(rng.integers(0, 240))
    sig_m = MOVE[di - LOOKBACK:di, li].mean()
    ub_m = max(day_open[di], pre_close[di]) * (1.0 + sig_m)
    lb_m = min(day_open[di], pre_close[di]) * (1.0 - sig_m)
    r = csv.iloc[di * 240 + li]
    err = max(abs(r.sigma - sig_m), abs(r.UB - ub_m), abs(r.LB - lb_m))
    worst = max(worst, err)
    if err < 1e-6:  # CSV 六位小数截断
        ok2 += 1
results.append((f"随机24点独立复算一致(最大误差{worst:.2e},容差1e-6)", ok2 == 24))

# 检查 3：1 分钟分辨率（非检查点步进）：抽样 6 日，相邻分钟 UB 不同占比
res_rows = []
ok3 = True
for d in ["2022-02-07", "2022-04-29", "2020-07-06", "2023-08-28", "2024-10-08", "2025-06-24"]:
    sub = csv[csv.date == d].reset_index(drop=True)
    diff_ratio = float((sub.UB.diff().abs() > 0).mean())
    nunq = int(sub.UB.nunique())
    res_rows.append((d, diff_ratio, nunq))
    ok3 &= diff_ratio > 0.95 and nunq > 200
results.append(("1分钟分辨率(6日相邻分钟UB变动占比>95%,唯一值>200/240)", bool(ok3), res_rows))

# 检查 4：检查点值与引擎决策值（sample CSV）一致
smp = pd.read_csv(OUT / "03_noise_bands_sample.csv")
SIG_BAR = {"13:00": "11:30"}
m = csv.merge(smp, left_on=["date", "price_label"], right_on=["date", "tau"], suffixes=("_1m", "_smp"))
m13 = smp[smp.tau == "13:00"].merge(csv, on="date", suffixes=("_smp", "_1m"))
m13 = m13[m13.price_label == "11:30"]
ok4a = len(m) == len(smp) - len(smp[smp.tau == "13:00"])
ok4b = bool(np.nanmax(np.abs(m.UB_1m - m.UB_smp)) < 1e-6) if len(m) else False
ok4c = bool(np.nanmax(np.abs(m13.UB_1m - m13.UB_smp)) < 1e-6) if len(m13) else False
results.append((f"检查点值=sample CSV(对齐{len(m)}行+13:00映射{len(m13)}行)", bool(ok4a and ok4b and ok4c)))

# 检查 5：图数据 CSV 与 1min CSV 一致
f1 = pd.read_csv(OUT / "10_fig1_data.csv")
f1ref = csv[csv.date == "2022-02-07"].reset_index(drop=True)
ok5a = bool(np.allclose(f1.UB, f1ref.UB, atol=1e-6) and np.allclose(f1.LB, f1ref.LB, atol=1e-6))
f4 = pd.read_csv(OUT / "10_fig4_data.csv")
f4ref = csv[csv.date == "2022-01-20"].reset_index(drop=True)
ok5b = bool(np.allclose(f4.UB, f4ref.UB, atol=1e-6) and np.allclose(f4.LB, f4ref.LB, atol=1e-6))
f2 = pd.read_csv(OUT / "10_fig2_data.csv")
ok5c = True
for d in ["2022-02-07", "2022-04-29"]:
    sub = f2[f2["case"].str.contains(d[:7])].reset_index(drop=True)
    ref = csv[csv.date == d].reset_index(drop=True)
    ok5c &= bool(len(sub) == 240 and np.allclose(sub.UB, ref.UB, atol=1e-6))
results.append(("图1/2/4数据CSV与1min带一致", bool(ok5a and ok5b and ok5c)))

# 检查 6：具体手算示例（写报告用）：2022-02-07 10:00
di = days.index("2022-02-07")
li = PLAB.index("10:00")
sig_m = MOVE[di - LOOKBACK:di, li].mean()
print("=== 手算示例 2022-02-07 10:00 ===")
print(f"day_open={day_open[di]:.3f} pre_close={pre_close[di]:.3f} sigma={sig_m:.6f}")
print(f"UB={max(day_open[di], pre_close[di]) * (1 + sig_m):.6f} "
      f"LB={min(day_open[di], pre_close[di]) * (1 - sig_m):.6f}")
print(f"前14日={days[di - LOOKBACK:di]}")
print()
print("=== 探针结果 ===")
allok = True
for r in results:
    print(("PASS" if r[1] else "FAIL"), "-", r[0])
    if len(r) > 2:
        for row in r[2]:
            print("     ", row)
    allok &= r[1]
print("ALL:", "PASS" if allok else "FAIL")
assert allok
