#!/usr/bin/env python
"""Generate main.ipynb for RUN-001 (Intraday_Momentum_for_ETF). Cells defined as strings."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CELLS = []


def md(src):
    CELLS.append({"cell_type": "markdown", "metadata": {}, "source": src})


def code(src):
    CELLS.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": src})


# ============================================================ title
md('''# RUN-001 · Intraday Momentum for ETF — A股复现（510300.SH）

论文：*Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)*
（Zarattini, Aziz, Barbon；SSRN 4824172，2025-09-22 版）

- 标的：510300.SH 沪深300ETF（华泰柏瑞）；基准：510300 自身 B&H；对照：000300.SH
- 样本：2017-01-03 ~ 2025-12-31（2,186 交易日，分钟数据上限）；日频预热自 2016-11-01
- 决策网格：g30（论文主线 7 时点）/ g15（14 时点）/ g05（42 时点）；变体 A/B/C × 三网格
- 成本：佣金 万1/边 + 滑点 ¥0.001/份/边（1 tick），ETF 免印花税；整手 100 份
- 可执行性：假设已有底仓可 T+0（用户 2026-10-04 裁决）；缓冲需求见 BLOCK-18
- 数据：局域网 MySQL 冻结快照（DT-001，QA 21/21 PASS）；bar 为 END 时间标签
  （09:30 竞价 bar + 09:31..11:30 / 13:01..15:00；信号=标签 τ bar 收盘，成交=下一分钟 bar 开盘）

本 notebook 按 plan_code.md BLOCK-00~18 组织，production 模式干净内核顺序执行。''')

# ============================================================ BLOCK-00
md('''## BLOCK-00 配置与公共函数

集中参数、路径、常量与公共函数。类型 NO_ARTIFACT。''')

code('''# BLOCK-00 配置与公共函数
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

ROOT = Path.cwd()
if not (ROOT / "data" / "processed").exists():
    ROOT = Path(r"D:\\quantitative_project\\复现工程\\Intraday_Momentum_for_ETF")
PROC = ROOT / "data" / "processed"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)
EXT_DIR = OUT / "ext"

RUN_ID = "RUN-001"
TS_CODE = "510300.SH"
TS_NAME = "沪深300ETF(华泰柏瑞)"
INIT_CAPITAL = 1_000_000.0
LOOKBACK = 14
VOL_MULT = 1.0
SIGMA_TARGET = 0.02
MAX_LEV = 4.0
COMMISSION_RATE = 0.0001   # 万1/边
SLIPPAGE_TICK = 0.001      # 元/份/边
LOT = 100
SAMPLE_START = pd.Timestamp("2017-01-01")
SAMPLE_END = pd.Timestamp("2025-12-31")


def make_grid(step_min, last_pm):
    am, pm = [], []
    t = 10 * 60
    while t <= 11 * 60:
        am.append(f"{t // 60:02d}:{t % 60:02d}")
        t += step_min
    t = 13 * 60
    last = int(last_pm[:2]) * 60 + int(last_pm[3:])
    while t <= last:
        pm.append(f"{t // 60:02d}:{t % 60:02d}")
        t += step_min
    return am + pm


GRIDS = {"g30": make_grid(30, "14:30"),
         "g15": make_grid(15, "14:45"),
         "g05": make_grid(5, "14:55")}
# END 标签 bar 语义：决策时点 τ 的信号 bar = 标签 τ（13:00 例外，用上午收盘 bar 11:30）；
# 成交 bar = 信号 bar 的下一分钟标签
SIG_BAR = {"13:00": "11:30"}

# CD-002 输出布局（DEC-010）：运行前清理 OUT 下旧产物，保留 ext（DT-001 冻结输入）
# 网格相关产物入 output\grids\<g> 子目录
import shutil
for _p in list(OUT.iterdir()):
    if _p.name == "ext":
        continue
    shutil.rmtree(_p) if _p.is_dir() else _p.unlink()
GRID_OUT = {}
for _g in GRIDS:
    GRID_OUT[_g] = OUT / "grids" / _g
    GRID_OUT[_g].mkdir(parents=True, exist_ok=True)


def label_key(s):
    return int(s[:2]) * 60 + int(s[3:])


def perf_stats(ret, equity, init=INIT_CAPITAL):
    r = np.asarray(ret, dtype=float)
    eq = np.asarray(equity, dtype=float)
    n = len(r)
    total = eq[-1] / init - 1.0
    irr = (1.0 + total) ** (252.0 / n) - 1.0 if (n > 0 and total > -1) else np.nan
    sd = r.std(ddof=1) if n > 1 else np.nan
    vol = sd * math.sqrt(252.0)
    sharpe = r.mean() / sd * math.sqrt(252.0) if (sd and sd > 0) else np.nan
    hit = float((r > 0).mean()) if n else np.nan
    peak = np.maximum.accumulate(eq)
    mdd = float((eq / peak - 1.0).min()) if n else np.nan
    skew = float(pd.Series(r).skew()) if n > 2 else np.nan
    return {"N": n, "TotalReturn": total, "IRR": irr, "Vol": vol, "Sharpe": sharpe,
            "HitRatio": hit, "MDD": mdd, "Skew": skew,
            "WorstDay": float(r.min()) if n else np.nan,
            "BestDay": float(r.max()) if n else np.nan,
            "AvgDailyBps": float(r.mean()) * 1e4 if n else np.nan}


def ols_stats(y, x):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = float(resid @ resid) / (n - 2)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    tvals = beta / se
    pvals = [math.erfc(abs(t) / math.sqrt(2.0)) for t in tvals]
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float(resid @ resid) / ss_tot if ss_tot > 0 else np.nan
    return {"alpha": float(beta[0]), "beta": float(beta[1]),
            "t_alpha": float(tvals[0]), "t_beta": float(tvals[1]),
            "p_alpha": float(pvals[0]), "p_beta": float(pvals[1]), "n": n, "r2": r2}


def rsi_wilder(close, n=5):
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = -d.clip(upper=0.0)
    au = up.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = au / ad
    return 100.0 - 100.0 / (1.0 + rs)


def dump_json(obj, name):
    p = OUT / name
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    return p


print("BLOCK-00 ok | grids:", {k: (len(v), v[0], v[-1]) for k, v in GRIDS.items()})
print("ROOT =", ROOT)
''')

# ============================================================ BLOCK-01
md('''## BLOCK-01 数据加载与分钟网格验证

加载 DT-001 冻结产物，验证 bar 标签集合（END 标签，241/日）、与日频交叉锚定、登记不完整日。
输出：`01_data_overview.json`、`01_daily_crosscheck.csv`、`01_incomplete_days.csv`。''')

code('''# BLOCK-01 数据加载与网格验证（510300.SH）
mn = pd.read_parquet(PROC / "minute_bars_510300.parquet")
daily = pd.read_csv(PROC / "daily_510300.csv", parse_dates=["trade_date"])
cal = pd.read_csv(PROC / "trade_calendar.csv", parse_dates=["cal_date"])
idx_daily = pd.read_csv(PROC / "index_daily_000300.csv", parse_dates=["trade_date"])

mn = mn[(mn.trade_date >= SAMPLE_START) & (mn.trade_date <= SAMPLE_END)].copy()
mn = mn.sort_values("trade_time").reset_index(drop=True)

# 标准标签集合（END 标签，时间序）：09:30 竞价 + 09:31..11:30 + 13:01..15:00
LABELS = sorted(mn.hhmm.unique(), key=label_key)
expected = (["09:30"] + [f"09:{m:02d}" for m in range(31, 60)]
            + [f"10:{m:02d}" for m in range(60)] + [f"11:{m:02d}" for m in range(31)]
            + [f"13:{m:02d}" for m in range(1, 60)] + [f"14:{m:02d}" for m in range(60)]
            + ["15:00"])
assert LABELS == expected, f"label set mismatch: {len(LABELS)}"
IDX = {s: i for i, s in enumerate(LABELS)}
PRICE_LABELS = LABELS[1:]           # 09:31..15:00（240 个价格时点）
PPos = {s: i for i, s in enumerate(PRICE_LABELS)}

bars_per_day = mn.groupby("trade_date").size()
incomplete = bars_per_day[bars_per_day != 241]
assert set(incomplete.index.strftime("%Y%m%d")) == {"20170809"} and incomplete.iloc[0] == 240

# 矩阵化：days x labels
days = pd.DatetimeIndex(sorted(mn.trade_date.unique()))
n_days, n_lab = len(days), len(LABELS)

def to_mat(col):
    piv = mn.pivot(index="trade_date", columns="hhmm", values=col)
    piv = piv.reindex(index=days, columns=LABELS)
    return piv.to_numpy(dtype=float)

O_m, H_m, L_m, C_m = to_mat("open"), to_mat("high"), to_mat("low"), to_mat("close")
VOL_m, AMT_m = to_mat("vol"), to_mat("amount")
assert not np.isnan(C_m[:, IDX["15:00"]]).any(), "15:00 close missing"

# 日 Open = 09:30 竞价 bar 开盘；2017-08-09 缺竞价 bar → 当日首根 bar 开盘
i0930 = IDX["09:30"]
first_valid = np.argmax(~np.isnan(O_m), axis=1)
day_open = np.where(np.isnan(O_m[:, i0930]), O_m[np.arange(n_days), first_valid], O_m[:, i0930])

# 与日频交叉锚定
dly = daily.set_index("trade_date").reindex(days)
agg_close = C_m[:, IDX["15:00"]]
d_close = np.abs(agg_close - dly["close"].to_numpy())
d_open = np.abs(day_open - dly["open"].to_numpy())
assert d_close.max() < 0.002 and d_open.max() < 0.002, (d_close.max(), d_open.max())

anchors = []
for d in ["2019-04-03", "2022-09-15", "2025-06-24"]:
    di = days.get_loc(pd.Timestamp(d))
    anchors.append({"date": d, "minute_close": float(agg_close[di]),
                    "daily_close": float(dly["close"].iloc[di]),
                    "abs_diff": float(abs(agg_close[di] - dly["close"].iloc[di]))})
    assert anchors[-1]["abs_diff"] < 0.002

pd.DataFrame({"trade_date": days, "close_minute": agg_close, "open_minute": day_open,
              "close_daily": dly["close"].to_numpy(), "open_daily": dly["open"].to_numpy(),
              "d_close": d_close, "d_open": d_open}).to_csv(OUT / "01_daily_crosscheck.csv", index=False)
pd.DataFrame({"trade_date": incomplete.index, "n_bars": incomplete.values,
              "reason": "missing 09:30 opening-auction bar (source gap, documented in DT-001)"}
             ).to_csv(OUT / "01_incomplete_days.csv", index=False)
overview = {"ts_code": TS_CODE, "days": int(n_days),
            "first_day": str(days[0].date()), "last_day": str(days[-1].date()),
            "minute_rows": int(len(mn)), "labels": n_lab,
            "bars_per_day": {"standard": 241, "exceptions": {"2017-08-09": 240}},
            "close_maxdiff": float(d_close.max()), "open_maxdiff": float(d_open.max()),
            "anchors": anchors}
dump_json(overview, "01_data_overview.json")
print(f"BLOCK-01 ok | days={n_days} labels={n_lab} close_maxdiff={d_close.max():.6f} open_maxdiff={d_open.max():.6f}")
print("anchors:", anchors)
''')

# ============================================================ BLOCK-02
md('''## BLOCK-02 日频序列与 σ_SPY,t

日收益（pct_chg/100，含分红口径）→ 14 日样本标准差（ddof=1，显式 shift(1)，开盘前可得）→ B&H 净值。
日频自 2016-11 起，σ_SPY,t 在样本首日即已预热完成。输出：`02_daily_series.csv`。''')

code('''# BLOCK-02 日频序列 / sigma14 / B&H
dl_full = daily.sort_values("trade_date").reset_index(drop=True)
dl_full["ret"] = dl_full["pct_chg"] / 100.0
dl_full["sigma14"] = dl_full["ret"].rolling(LOOKBACK).std(ddof=1).shift(1)   # t 日开盘前可得
assert dl_full["sigma14"].iloc[:LOOKBACK].isna().all()
assert dl_full["sigma14"].iloc[LOOKBACK:].notna().all()

# 手工复算 3 日 sigma14
for d in ["2017-01-03", "2020-07-06", "2025-06-24"]:
    i = dl_full.index[dl_full.trade_date == pd.Timestamp(d)][0]
    manual = dl_full["ret"].iloc[i - LOOKBACK:i].std(ddof=1)
    assert abs(manual - dl_full["sigma14"].iloc[i]) < 1e-12, (d, manual, dl_full["sigma14"].iloc[i])

s = dl_full.set_index("trade_date")
sample_mask = (s.index >= SAMPLE_START) & (s.index <= SAMPLE_END)
pre_close_v = s["pre_close"].reindex(days).to_numpy()
ret_v = s["ret"].reindex(days).to_numpy()
sigma14_v = s["sigma14"].reindex(days).to_numpy()
assert not np.isnan(pre_close_v).any() and not np.isnan(ret_v).any()
assert not np.isnan(sigma14_v).any(), "sigma14 应已借 2016-11 起日频完成预热"

bh_nav = np.cumprod(1.0 + ret_v)
manual_nav = float((1.0 + pd.Series(ret_v)).prod())
assert abs(bh_nav[-1] - manual_nav) < 1e-9

pd.DataFrame({"date": days, "open": day_open, "close": agg_close, "pre_close": pre_close_v,
              "ret": ret_v, "sigma14": sigma14_v, "bh_nav": bh_nav}
             ).to_csv(OUT / "02_daily_series.csv", index=False)
print(f"BLOCK-02 ok | sigma14 range=[{np.nanmin(sigma14_v):.5f},{np.nanmax(sigma14_v):.5f}] "
      f"bh_nav_end={bh_nav[-1]:.4f}")
''')

# ============================================================ BLOCK-03
md('''## BLOCK-03 噪声带（Noise Area）

$move_{d,\\tau}=|Close_{d,\\tau}/Open_d-1|$；$\\sigma_{t,\\tau}$=前 14 个交易日同列均值
（rolling(14).mean().shift(1)，t 日开盘前可得）；
$UB=\\max(Open_t,preClose_t)\\times(1+VM\\cdot\\sigma)$，$LB=\\min(Open_t,preClose_t)\\times(1-VM\\cdot\\sigma)$。
σ 与 UB/LB 均在**全部 240 个 1 分钟价格标签**上计算（τ 为 1 分钟离散时点，与论文 §3 一致）；
交易决策只在网格时点评估（引擎不变）。
输出：`03_noise_bands_sample.csv`（全部日 × g30 决策时点 + 15:00）、
`03_noise_bands_1min.csv`（全部日 × 240 个 1 分钟时点全分辨率，DEC-012）、`03_sigma_shape.csv`。''')

code('''# BLOCK-03 噪声带
P_m = C_m[:, 1:]                       # days x 240 price labels
MOVE = np.abs(P_m / day_open[:, None] - 1.0)

def make_sigma(lookback):
    return pd.DataFrame(MOVE).rolling(lookback).mean().shift(1).to_numpy()

SIGMA = {LOOKBACK: make_sigma(LOOKBACK)}
assert np.isnan(SIGMA[LOOKBACK][:LOOKBACK]).all()          # 前 14 个样本日无带 → 不交易
assert not np.isnan(SIGMA[LOOKBACK][LOOKBACK:]).any()

# 手工复算 3 个 (d, tau)
for d, tau in [("2017-02-03", "10:00"), ("2021-03-15", "13:30"), ("2025-06-24", "14:30")]:
    di = days.get_loc(pd.Timestamp(d))
    pi_ = PPos[tau]
    manual = np.nanmean(MOVE[di - LOOKBACK:di, pi_])
    assert abs(manual - SIGMA[LOOKBACK][di, pi_]) < 1e-12, (d, tau)

def bands_for(di, vm, lookback=LOOKBACK):
    sg = SIGMA[lookback][di]
    base_up = max(day_open[di], pre_close_v[di])
    base_dn = min(day_open[di], pre_close_v[di])
    return base_up * (1.0 + vm * sg), base_dn * (1.0 - vm * sg)

# 输出：全部日 × (g30 决策时点 + 15:00)
rows = []
out_taus = GRIDS["g30"] + ["15:00"]
for di in range(n_days):
    ub, lb = bands_for(di, VOL_MULT)
    for tau in out_taus:
        pi_ = PPos[tau if tau != "13:00" else "11:30"]
        rows.append((days[di], tau, SIGMA[LOOKBACK][di, pi_], ub[pi_], lb[pi_]))
pd.DataFrame(rows, columns=["date", "tau", "sigma", "UB", "LB"]).to_csv(
    OUT / "03_noise_bands_sample.csv", index=False)

# DEC-012：1 分钟全分辨率噪声带（全部日 × 240 个价格标签；与引擎/图形同一 σ 矩阵）
SG_FULL = SIGMA[LOOKBACK]
BASE_UP = np.maximum(day_open, pre_close_v)          # max(Open_t, preClose_t)
BASE_DN = np.minimum(day_open, pre_close_v)          # min(Open_t, preClose_t)
UB_1M = BASE_UP[:, None] * (1.0 + VOL_MULT * SG_FULL)
LB_1M = BASE_DN[:, None] * (1.0 - VOL_MULT * SG_FULL)
for d in ("2018-06-11", "2022-04-29", "2025-06-24"):  # 与 bands_for 逐日一致性抽查
    di_ = days.get_loc(pd.Timestamp(d))
    ub_, lb_ = bands_for(di_, VOL_MULT)
    assert np.allclose(UB_1M[di_], ub_, equal_nan=True) and np.allclose(LB_1M[di_], lb_, equal_nan=True)
pd.DataFrame({"date": np.repeat(days, len(PRICE_LABELS)),
              "price_label": np.tile(PRICE_LABELS, n_days),
              "sigma": SG_FULL.ravel(), "UB": UB_1M.ravel(), "LB": LB_1M.ravel()}
             ).to_csv(OUT / "03_noise_bands_1min.csv", index=False, float_format="%.6f")
pd.DataFrame({"price_label": PRICE_LABELS,
              "sigma_mean": np.nanmean(SIGMA[LOOKBACK], axis=0)}).to_csv(
    OUT / "03_sigma_shape.csv", index=False)
sm = np.nanmean(SIGMA[LOOKBACK][LOOKBACK:], axis=0)
assert sm[-1] > sm[0], "sigma 应随时点上升"
print(f"BLOCK-03 ok | sigma(09:31)={sm[0]:.4%} sigma(15:00)={sm[-1]:.4%} "
      f"range=[{np.nanmin(SIGMA[LOOKBACK][LOOKBACK:]):.4%},{np.nanmax(SIGMA[LOOKBACK]):.4%}]")
''')

# ============================================================ BLOCK-04
md('''## BLOCK-04 VWAP（按决策间隔 bar 聚合，DEC-009）

网格 bar =（前一信号标签, 当前信号标签] 的 1 分钟 bar 合计（首根自 09:30 含竞价 bar 起；13:00 决策点用 11:30 bar；午休无 bar 自然跳过）：
$VWAP_{g,\\tau}=\\dfrac{\\sum_{bar\\le\\tau} close_{bar}\\cdot vol_{bar}}{(\\sum_{bar\\le\\tau} vol_{bar})\\times 100}$
（vol 手 → 份；零成交 bar 不产生增量）。仅用截至 τ 的日内累计网格 bar，无前视；与论文"检查时间间隔"数据粒度一致。
输出：`grids\\<g>\\04_vwap_check.csv`（每网格）。''')

code('''# BLOCK-04 VWAP（网格口径，用户 2026-10-05 裁决）
def grid_bars(g):
    sigs = [SIG_BAR.get(t, t) for t in GRIDS[g]] + ["15:00"]
    cols, c0 = [], 0
    for slab in sigs:
        c1 = IDX[slab]
        cols.append((slab, c0, c1))
        c0 = c1 + 1
    assert cols[-1][2] == IDX["15:00"] and c0 == n_lab
    return cols


GRID_BARS = {g: grid_bars(g) for g in GRIDS}
VWAP_G = {}
for g, cols in GRID_BARS.items():
    pv = np.zeros((n_days, len(cols)))
    vv = np.zeros((n_days, len(cols)))
    for k, (slab, c0, c1) in enumerate(cols):
        close_k = C_m[:, c1]                     # 网格 bar 收盘 = 末端 1 分钟 bar 收盘
        vol_k = np.nansum(np.where(np.isnan(VOL_m[:, c0:c1 + 1]), 0.0, VOL_m[:, c0:c1 + 1]), axis=1)
        bad = np.isnan(close_k)                   # 缺口 bar（如 2017-08-09 缺竞价 bar）该根贡献置零
        pv[:, k] = np.where(bad, 0.0, close_k * vol_k)
        vv[:, k] = np.where(bad, 0.0, vol_k)
    cs_pv = np.cumsum(pv, axis=1)
    cs_vv = np.cumsum(vv, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = np.where(cs_vv > 0, cs_pv / cs_vv, np.nan)   # close×vol 与 vol 同单位，无需 ×100
    arr = np.full((n_days, n_lab), np.nan)       # 仅信号列有值，引擎只读信号列
    for k, (slab, c0, c1) in enumerate(cols):
        arr[:, c1] = vw[:, k]
    assert not np.isnan(arr[:, [c1 for _, _, c1 in cols]]).any()
    VWAP_G[g] = arr

# 手工复算：每网格 3 个 (d, tau)，独立标量路径
def manual_vwap(di, g, tau):
    slab = SIG_BAR.get(tau, tau)
    num = den = 0.0
    for lab, a, b in GRID_BARS[g]:
        vb = 0.0
        for c in range(a, b + 1):
            x = VOL_m[di, c]
            vb += 0.0 if x != x else x
        cl = C_m[di, b]
        if cl == cl:
            num += cl * vb
            den += vb
        if lab == slab:
            break
    return num / den


checks = []
for g in GRIDS:
    for d, tau in [("2019-04-03", GRIDS[g][1]), ("2022-09-15", GRIDS[g][-3]), ("2025-06-24", GRIDS[g][-1])]:
        di = days.get_loc(pd.Timestamp(d))
        got = VWAP_G[g][di, IDX[SIG_BAR.get(tau, tau)]]
        man = manual_vwap(di, g, tau)
        assert abs(got - man) < 1e-9, (g, d, tau, got, man)
        checks.append({"grid": g, "date": d, "tau": tau, "vwap": float(got), "manual": float(man)})

# 每网格随机 20 日 × 全部决策时点导出
rng20 = np.random.RandomState(42).choice(n_days, 20, replace=False)
for g in GRIDS:
    rows = []
    for di in sorted(rng20):
        for tau in GRIDS[g] + ["15:00"]:
            rows.append((days[di], tau, VWAP_G[g][di, IDX[SIG_BAR.get(tau, tau)]],
                         manual_vwap(di, g, tau)))
    pd.DataFrame(rows, columns=["date", "tau", "vwap", "manual"]).to_csv(
        GRID_OUT[g] / "04_vwap_check.csv", index=False)

# 数量级：日内 VWAP(15:00) ≈ 日线 amount/vol 均价（尺度断言，防止单位错误）
dly_avg = (dly["amount"].to_numpy() * 1000.0) / (dly["vol"].to_numpy() * 100.0)
for g in GRIDS:
    rel = np.abs(VWAP_G[g][:, IDX["15:00"]] / dly_avg - 1.0)
    assert np.nanmedian(rel) < 0.01 and np.nanmax(rel) < 0.05, (g, np.nanmedian(rel), np.nanmax(rel))
    print(f"BLOCK-04 {g} | vwap(15:00) vs daily avg rel diff: median={np.nanmedian(rel):.4%} max={np.nanmax(rel):.4%}")
print("checks:", checks)
''')

# ============================================================ BLOCK-05
md('''## BLOCK-05 回测引擎与变体 A（Opposite Band）

引擎规格（plan_code.md BLOCK-05）：
- 决策 τ ∈ grid；信号价 p(τ)=标签 τ bar 收盘（13:00 用 11:30 bar）；成交价=下一分钟 bar 开盘；15:00 强平=15:00 bar 收盘
- 空仓且**新跨越**上带 → 开多；新跨越下带 → 开空（armed 机制：价格回到带内/另一侧后重新武装）
- 变体 A 止损=反向带（持多 p<LB 平多+反手开空；对称）；15:00 强制平仓
- 份额=floor(AUM×lev/Open/100)×100；成本=佣金×成交额+滑点×份额，双边；每网格独立资金线
- 成交前查 tradability：该分钟不可买/不可卖则放弃本次委托

输出：`grids\<g>\05_oppband_{trades,daily_returns,equity}.csv`、`05_meta.json`。''')

code('''# BLOCK-05 引擎 + 变体 A（三网格）
trad = pd.read_csv(PROC / "tradability.csv", dtype={"交易日期": str, "交易时间": str})
trad["label"] = trad["交易时间"].str[:2] + ":" + trad["交易时间"].str[2:]
trad["trade_date"] = pd.to_datetime(trad["交易日期"], format="%Y%m%d")
BUYABLE = np.ones((n_days, n_lab), dtype=bool)
SELLABLE = np.ones((n_days, n_lab), dtype=bool)
day_pos = {d: i for i, d in enumerate(days)}
tb = trad[trad["可买"] == 0]
for r in tb.itertuples():
    BUYABLE[day_pos[r.trade_date], IDX[r.label]] = False
ts_ = trad[trad["可卖"] == 0]
for r in ts_.itertuples():
    SELLABLE[day_pos[r.trade_date], IDX[r.label]] = False
# 零成交分钟（含 2024-09-27 上交所技术故障 6 根）不可成交：双边封锁
tz = trad[trad["是否有成交"] == 0]
for r in tz.itertuples():
    BUYABLE[day_pos[r.trade_date], IDX[r.label]] = False
    SELLABLE[day_pos[r.trade_date], IDX[r.label]] = False
print(f"tradability gates: buy-blocked={int((~BUYABLE).sum())} sell-blocked={int((~SELLABLE).sum())} "
      f"(incl. zero-activity minutes={len(tz)}; none at 15:00)")

# 网格规格：(tau, sig_col, exec_col, price_pos)
GRID_SPEC = {}
for g, taus in GRIDS.items():
    spec = []
    for tau in taus:
        sbar = SIG_BAR.get(tau, tau)
        sc = IDX[sbar]
        ec = IDX[LABELS[sc + 1]]          # 信号 bar 的下一分钟标签
        spec.append((tau, sc, ec, PPos[sbar]))
    GRID_SPEC[g] = spec
for g, spec in GRID_SPEC.items():
    for tau, sc, ec, _ in spec:
        assert label_key(LABELS[sc]) <= label_key(LABELS[ec]), (g, tau)

# 引擎热路径用 Python list（np.float64 标量运算慢 3-5 倍）
C_l = C_m.tolist()
O_l = O_m.tolist()
VW_G_l = {g: VWAP_G[g].tolist() for g in GRIDS}   # CD-002：VWAP 按网格口径（DEC-009）
BUY_l = BUYABLE.tolist()
SELL_l = SELLABLE.tolist()
s14_l = sigma14_v.tolist()
do_l = day_open.tolist()
pc_l = pre_close_v.tolist()


def run_backtest(grid, stop_mode, dyn_lev=False, vm=1.0, lookback=LOOKBACK,
                 commission=COMMISSION_RATE, slippage=SLIPPAGE_TICK,
                 sigma_target=SIGMA_TARGET, max_lev=MAX_LEV, tag=""):
    if lookback not in SIGMA:
        SIGMA[lookback] = make_sigma(lookback)
    sig_l = SIGMA[lookback].tolist()
    spec = GRID_SPEC[grid]
    i1500 = IDX["15:00"]
    trades = []
    daily_rows = []
    aum = INIT_CAPITAL
    tid = 0
    isnan = math.isnan
    floor = math.floor
    for di in range(n_days):
        aum0 = aum
        pnl_day = 0.0
        n_tr = 0
        s14 = s14_l[di]
        if dyn_lev:
            if isnan(s14) or s14 <= 0:
                daily_rows.append((days[di], aum0, aum0, 0.0, 0, np.nan, 0))
                continue
            lev = min(max_lev, sigma_target / s14)
        else:
            lev = 1.0
        do = do_l[di]
        pc = pc_l[di]
        shares = floor(aum0 * lev / do / 100.0) * 100
        if shares <= 0:
            daily_rows.append((days[di], aum0, aum0, 0.0, 0, lev, 0))
            continue
        base_up = do if do > pc else pc
        base_dn = do if do < pc else pc
        Crow = C_l[di]
        Orow = O_l[di]
        VWrow = VW_G_l[grid][di]
        SGrow = sig_l[di]
        BUYrow = BUY_l[di]
        SELLrow = SELL_l[di]
        pos = 0
        entry_px = 0.0
        entry_comm = 0.0
        entry_slip = 0.0
        entry_tau = ""
        entry_tid = 0
        armed_l = True
        armed_s = True
        for tau, sc, ec, pi_ in spec:
            p = Crow[sc]
            if p != p:
                continue
            sg = SGrow[pi_]
            if sg != sg:
                continue
            ub = base_up * (1.0 + vm * sg)
            lb = base_dn * (1.0 - vm * sg)
            if p <= ub:
                armed_l = True
            if p >= lb:
                armed_s = True
            ep = Orow[ec]
            if ep != ep:
                continue
            if pos == 0:
                if p > ub and armed_l and BUYrow[ec]:
                    tid += 1
                    entry_tid = tid
                    entry_comm = ep * shares * commission
                    entry_slip = shares * slippage
                    entry_px = ep
                    entry_tau = tau
                    pos = 1
                    armed_l = False
                    trades.append((days[di], tau, LABELS[ec], "买入", ep, shares,
                                   entry_comm, entry_slip, tid, "OPEN_LONG", "", lev))
                    n_tr += 1
                elif p < lb and armed_s and SELLrow[ec]:
                    tid += 1
                    entry_tid = tid
                    entry_comm = ep * shares * commission
                    entry_slip = shares * slippage
                    entry_px = ep
                    entry_tau = tau
                    pos = -1
                    armed_s = False
                    trades.append((days[di], tau, LABELS[ec], "卖出", ep, shares,
                                   entry_comm, entry_slip, tid, "OPEN_SHORT", "", lev))
                    n_tr += 1
            elif pos == 1:
                vw = VWrow[sc]
                if stop_mode == "opp_band":
                    stop = lb
                elif stop_mode == "vwap_only":
                    stop = vw if vw == vw else lb
                else:
                    stop = max(ub, vw) if vw == vw else ub
                if p < stop and SELLrow[ec]:
                    exit_comm = ep * shares * commission
                    exit_slip = shares * slippage
                    pnl_day += (ep - entry_px) * shares - entry_comm - entry_slip - exit_comm - exit_slip
                    trades.append((days[di], tau, LABELS[ec], "卖出", ep, shares,
                                   exit_comm, exit_slip, entry_tid, "CLOSE_LONG", stop_mode, lev))
                    n_tr += 1
                    pos = 0
                    if p < lb and armed_s and SELLrow[ec]:
                        tid += 1
                        entry_tid = tid
                        entry_comm = ep * shares * commission
                        entry_slip = shares * slippage
                        entry_px = ep
                        entry_tau = tau
                        pos = -1
                        armed_s = False
                        trades.append((days[di], tau, LABELS[ec], "卖出", ep, shares,
                                       entry_comm, entry_slip, tid, "OPEN_SHORT", "REVERSAL", lev))
                        n_tr += 1
            elif pos == -1:
                vw = VWrow[sc]
                if stop_mode == "opp_band":
                    stop = ub
                elif stop_mode == "vwap_only":
                    stop = vw if vw == vw else ub
                else:
                    stop = min(lb, vw) if vw == vw else lb
                if p > stop and BUYrow[ec]:
                    exit_comm = ep * shares * commission
                    exit_slip = shares * slippage
                    pnl_day += (entry_px - ep) * shares - entry_comm - entry_slip - exit_comm - exit_slip
                    trades.append((days[di], tau, LABELS[ec], "买入", ep, shares,
                                   exit_comm, exit_slip, entry_tid, "CLOSE_SHORT", stop_mode, lev))
                    n_tr += 1
                    pos = 0
                    if p > ub and armed_l and BUYrow[ec]:
                        tid += 1
                        entry_tid = tid
                        entry_comm = ep * shares * commission
                        entry_slip = shares * slippage
                        entry_px = ep
                        entry_tau = tau
                        pos = 1
                        armed_l = False
                        trades.append((days[di], tau, LABELS[ec], "买入", ep, shares,
                                       entry_comm, entry_slip, tid, "OPEN_LONG", "REVERSAL", lev))
                        n_tr += 1
        if pos != 0:
            ep = Crow[i1500]
            exit_comm = ep * shares * commission
            exit_slip = shares * slippage
            if pos == 1:
                pnl_day += (ep - entry_px) * shares - entry_comm - entry_slip - exit_comm - exit_slip
                trades.append((days[di], "15:00", "15:00", "卖出", ep, shares,
                               exit_comm, exit_slip, entry_tid, "CLOSE_LONG", "EOD", lev))
            else:
                pnl_day += (entry_px - ep) * shares - entry_comm - entry_slip - exit_comm - exit_slip
                trades.append((days[di], "15:00", "15:00", "买入", ep, shares,
                               exit_comm, exit_slip, entry_tid, "CLOSE_SHORT", "EOD", lev))
            n_tr += 1
        if aum0 + pnl_day <= 0:
            raise RuntimeError(f"equity non-positive at {days[di].date()}")
        aum = aum0 + pnl_day
        daily_rows.append((days[di], aum0, aum, pnl_day / aum0, n_tr, lev, 1 if n_tr > 0 else 0))
    tr = pd.DataFrame(trades, columns=["date", "decision_time", "exec_time", "side", "price",
                                       "shares", "commission", "slippage_cost", "trade_id",
                                       "action", "reason", "lev"])
    tr["cost"] = tr["commission"] + tr["slippage_cost"]
    dl = pd.DataFrame(daily_rows, columns=["date", "aum_start", "aum_end", "ret",
                                           "n_exec", "lev", "traded"])
    eq = dl[["date", "aum_end"]].copy()
    eq["nav"] = eq["aum_end"] / INIT_CAPITAL
    return {"trades": tr, "daily": dl, "equity": eq,
            "params": {"grid": grid, "stop_mode": stop_mode, "dyn_lev": dyn_lev, "vm": vm,
                       "lookback": lookback, "commission": commission, "slippage": slippage,
                       "sigma_target": sigma_target, "max_lev": max_lev, "tag": tag}}


def save_run(res, prefix):
    g = res["params"]["grid"]
    d = GRID_OUT[g]                                # CD-002：网格产物入 grids\<g>\（DEC-010）
    res["trades"].to_csv(d / f"{prefix}_trades.csv", index=False)
    res["daily"].to_csv(d / f"{prefix}_daily_returns.csv", index=False)
    res["equity"].to_csv(d / f"{prefix}_equity.csv", index=False)


RUNS = {}
for g in ["g30", "g15", "g05"]:
    res = run_backtest(g, "opp_band", dyn_lev=False, tag=f"A_{g}")
    RUNS[("A", g)] = res
    save_run(res, "05_oppband")
    # 现金账连续性勾稽：AUM 递推 == sum(pnl)
    rec = res["daily"]
    chk = np.abs(rec["aum_end"].to_numpy() - (INIT_CAPITAL + (rec["ret"] * rec["aum_start"]).cumsum().to_numpy())).max()
    assert chk < 1e-6, chk
    assert (res["equity"]["aum_end"] > 0).all()
    print(f"variant A {g}: exec_rows={len(res['trades'])} days_traded={int(res['daily']['traded'].sum())} "
          f"end_aum={res['daily']['aum_end'].iloc[-1]:,.0f} aum_recursion_maxdiff={chk:.2e}")

dump_json({"variant": "A opp_band", "grids": {g: {"exec_rows": int(len(RUNS[("A", g)]["trades"])),
           "end_aum": float(RUNS[("A", g)]["daily"]["aum_end"].iloc[-1])} for g in GRIDS}}, "05_meta.json")

# 抽 1 笔手工复算（g30 首笔开仓）
t0 = RUNS[("A", "g30")]["trades"].iloc[0]
di0 = day_pos[pd.Timestamp(t0["date"])]
manual_px = O_m[di0, IDX[t0["exec_time"]]]
assert abs(manual_px - t0["price"]) < 1e-9
assert abs(t0["commission"] - t0["price"] * t0["shares"] * COMMISSION_RATE) < 1e-9
assert t0["shares"] % 100 == 0
print("manual trade recheck ok:", t0[["date", "decision_time", "exec_time", "side", "price", "shares"]].to_dict())
''')

# ============================================================ BLOCK-06
md('''## BLOCK-06 变体 B（Current Band + VWAP）

持多止损 = max(UB, VWAP)，持空止损 = min(LB, VWAP)；价格同时穿越反向带则平仓+反手；
止损后不原地再入（armed 机制需新跨越）。输出：`grids\<g>\06_bandvwap_*.csv`、`06_meta.json`。''')

code('''# BLOCK-06 变体 B（三网格）
for g in ["g30", "g15", "g05"]:
    res = run_backtest(g, "band_vwap", dyn_lev=False, tag=f"B_{g}")
    RUNS[("B", g)] = res
    save_run(res, "06_bandvwap")
    nA = len(RUNS[("A", g)]["trades"])
    nB = len(res["trades"])
    assert (res["equity"]["aum_end"] > 0).all()
    print(f"variant B {g}: exec_rows={nB} (A={nA}, B/A={nB / nA:.2f}) "
          f"end_aum={res['daily']['aum_end'].iloc[-1]:,.0f}")

# 抽 3 个止损案例核对 stop = max(UB, VWAP)
tb30 = RUNS[("B", "g30")]["trades"]
cl = tb30[tb30.action == "CLOSE_LONG"].head(3)
for r in cl.itertuples():
    di = day_pos[pd.Timestamp(r.date)]
    sc = IDX[SIG_BAR.get(r.decision_time, r.decision_time)]
    pi_ = PPos[SIG_BAR.get(r.decision_time, r.decision_time)]
    sg = SIGMA[LOOKBACK][di, pi_]
    ub = max(day_open[di], pre_close_v[di]) * (1 + sg)
    vw = VWAP_G["g30"][di, sc]
    p = C_m[di, sc]
    assert p < max(ub, vw), (r.date, r.decision_time)
dump_json({"variant": "B band_vwap",
           "grids": {g: {"exec_rows": int(len(RUNS[("B", g)]["trades"])),
                         "end_aum": float(RUNS[("B", g)]["daily"]["aum_end"].iloc[-1])} for g in GRIDS}},
          "06_meta.json")
print("BLOCK-06 ok | 3 stop cases verified (p < max(UB,VWAP))")
''')

# ============================================================ BLOCK-07
md('''## BLOCK-07 变体 C（B + 波动率目标动态仓位）

$lev_t=\\min(4,\\ \\sigma_{target}/\\sigma_{SPY,t})$，$\\sigma_{target}=2\\%$；
份额=floor(AUM×lev/Open/100)×100；止损同变体 B。输出：`grids\<g>\07_dynamic_*.csv`、`07_leverage.csv`（网格无关，根目录）、`07_meta.json`。''')

code('''# BLOCK-07 变体 C（三网格）
for g in ["g30", "g15", "g05"]:
    res = run_backtest(g, "band_vwap", dyn_lev=True, tag=f"C_{g}")
    RUNS[("C", g)] = res
    save_run(res, "07_dynamic")
    lev_v = res["daily"]["lev"].dropna()
    assert (lev_v > 0).all() and (lev_v <= MAX_LEV + 1e-12).all()
    assert (res["equity"]["aum_end"] > 0).all()
    print(f"variant C {g}: exec_rows={len(res['trades'])} end_aum={res['daily']['aum_end'].iloc[-1]:,.0f} "
          f"lev mean={lev_v.mean():.2f} max={lev_v.max():.2f}")

# 抽 3 日手工复算 lev 与份额
rc = RUNS[("C", "g30")]["daily"]
for d in ["2018-06-11", "2021-09-01", "2025-06-24"]:
    row = rc[rc.date == pd.Timestamp(d)].iloc[0]
    di = day_pos[pd.Timestamp(d)]
    lev_manual = min(MAX_LEV, SIGMA_TARGET / sigma14_v[di])
    assert abs(row.lev - lev_manual) < 1e-12, (d, row.lev, lev_manual)
    sh_manual = math.floor(row.aum_start * lev_manual / day_open[di] / 100.0) * 100
    tr_d = RUNS[("C", "g30")]["trades"]
    td = tr_d[tr_d.date == pd.Timestamp(d)]
    if len(td):
        assert td["shares"].iloc[0] == sh_manual, (d, td["shares"].iloc[0], sh_manual)

lev_all = rc[["date", "lev", "aum_start"]].copy()
lev_all["notional"] = lev_all["lev"] * lev_all["aum_start"]
lev_all.to_csv(OUT / "07_leverage.csv", index=False)
dump_json({"variant": "C dynamic",
           "grids": {g: {"exec_rows": int(len(RUNS[("C", g)]["trades"])),
                         "end_aum": float(RUNS[("C", g)]["daily"]["aum_end"].iloc[-1]),
                         "lev_mean": float(RUNS[("C", g)]["daily"]["lev"].mean()),
                         "lev_max": float(RUNS[("C", g)]["daily"]["lev"].max())} for g in GRIDS}},
          "07_meta.json")
print("BLOCK-07 ok | lev/shares manual recheck passed")
''')

# ============================================================ BLOCK-08
md('''## BLOCK-08 汇总统计（Tables 1/2/3/A1）+ Alpha/Beta

Total Return、IRR（(1+TR)^(252/N)−1）、Vol、Sharpe（rf=0）、Hit Ratio（全样本日 + traded-days 两口径）、
MDD、Skew、Worst/Best Day；日频 OLS：RetMom = α + β·RetETF + ε（α 年化 ×252）。
输出：`08_summary_stats.csv`（变体×网格 + B&H）、`08_alpha_beta.csv`。''')

code('''# BLOCK-08 汇总统计 + alpha/beta
rows = []
ab_rows = []
for (v, g), res in RUNS.items():
    dl = res["daily"]
    st = perf_stats(dl["ret"], dl["aum_end"])
    traded = dl[dl["traded"] == 1]
    st["HitRatioTraded"] = float((traded["ret"] > 0).mean()) if len(traded) else np.nan
    st["TradedDays"] = int(len(traded))
    st["Variant"] = v
    st["Grid"] = g
    rows.append(st)
    ab = ols_stats(dl["ret"].to_numpy(), ret_v)
    ab_rows.append({"Variant": v, "Grid": g, "alpha_daily": ab["alpha"],
                    "alpha_annual": ab["alpha"] * 252.0, "beta": ab["beta"],
                    "t_alpha": ab["t_alpha"], "t_beta": ab["t_beta"],
                    "p_alpha": ab["p_alpha"], "p_beta": ab["p_beta"], "n": ab["n"], "r2": ab["r2"]})
st = perf_stats(ret_v, bh_nav * INIT_CAPITAL)
st.update({"HitRatioTraded": np.nan, "TradedDays": int((ret_v != 0).sum()),
           "Variant": "BH", "Grid": "-"})
rows.append(st)

SUMMARY = pd.DataFrame(rows)[["Variant", "Grid", "N", "TradedDays", "TotalReturn", "IRR", "Vol",
                              "Sharpe", "HitRatio", "HitRatioTraded", "MDD", "Skew",
                              "WorstDay", "BestDay", "AvgDailyBps"]]
SUMMARY.to_csv(OUT / "08_summary_stats.csv", index=False)
ALPHA_BETA = pd.DataFrame(ab_rows)
ALPHA_BETA.to_csv(OUT / "08_alpha_beta.csv", index=False)

# 勾稽：TotalReturn == equity 末值/初值 - 1
for (v, g), res in RUNS.items():
    tr_direct = res["equity"]["nav"].iloc[-1] - 1.0
    got = SUMMARY[(SUMMARY.Variant == v) & (SUMMARY.Grid == g)]["TotalReturn"].iloc[0]
    assert abs(tr_direct - got) < 1e-12, (v, g)
pd.set_option("display.float_format", lambda x: f"{x:,.4f}")
print("BLOCK-08 ok")
print(SUMMARY[SUMMARY.Grid.isin(["g30", "-"])].to_string(index=False))
''')

# ============================================================ BLOCK-09
md('''## BLOCK-09 交易级统计（Table 4）

trade = 整趟持仓（开→平）；PnL/Share = 整趟净盈亏/份额（含成本）；Max Loss/Gain 按整趟收益率。
输出：`09_trade_level_stats.csv`、`09_round_trips_{variant}_{grid}.csv`。''')

code('''# BLOCK-09 交易级统计
def round_trips(tr):
    rts = []
    for tid, grp in tr.groupby("trade_id"):
        grp = grp.sort_index()
        op = grp[grp.action.str.startswith("OPEN")]
        cl = grp[grp.action.str.startswith("CLOSE")]
        if len(op) != 1 or len(cl) < 1:
            raise RuntimeError(f"bad round trip {tid}")
        o = op.iloc[0]
        c = cl.iloc[-1]
        direction = 1 if o.action == "OPEN_LONG" else -1
        gross = direction * (c["price"] - o["price"]) * o["shares"]
        costs = grp["cost"].sum()
        pnl = gross - costs
        rts.append({"trade_id": tid, "date": o["date"], "direction": "long" if direction == 1 else "short",
                    "entry_time": o["decision_time"], "exit_time": c["decision_time"],
                    "entry_px": o["price"], "exit_px": c["price"], "shares": o["shares"],
                    "gross": gross, "costs": costs, "pnl": pnl,
                    "pnl_per_share": pnl / o["shares"],
                    "ret_on_notional": pnl / (o["price"] * o["shares"]),
                    "n_exec": len(grp)})
    return pd.DataFrame(rts)


RT = {}
rows = []
for (v, g), res in RUNS.items():
    rt = round_trips(res["trades"])
    RT[(v, g)] = rt
    rt.to_csv(GRID_OUT[g] / f"09_round_trips_{v}.csv", index=False)
    ndays = len(res["daily"])
    worst = rt.loc[rt["ret_on_notional"].idxmin()]
    best = rt.loc[rt["ret_on_notional"].idxmax()]
    rows.append({"Variant": v, "Grid": g, "Trades": len(rt),
                 "AvgTradePerDay": len(rt) / ndays,
                 "HitRatio": float((rt["pnl"] > 0).mean()),
                 "AvgPnLPerShare": float(rt["pnl_per_share"].mean()),
                 "AvgRetOnNotionalBps": float(rt["ret_on_notional"].mean()) * 1e4,
                 "MaxLossTradePct": float(worst["ret_on_notional"]) * 100,
                 "MaxLossDate": str(pd.Timestamp(worst["date"]).date()),
                 "MaxGainTradePct": float(best["ret_on_notional"]) * 100,
                 "MaxGainDate": str(pd.Timestamp(best["date"]).date()),
                 "LongShare": float((rt["direction"] == "long").mean())})
TLS = pd.DataFrame(rows)
TLS.to_csv(OUT / "09_trade_level_stats.csv", index=False)
# 勾稽：整趟数 = trades 文件 OPEN 行数；hit 与符号一致；日盈亏合计 == 整趟 pnl 合计
for (v, g), res in RUNS.items():
    n_open = int(res["trades"]["action"].str.startswith("OPEN").sum())
    assert n_open == len(RT[(v, g)]), (v, g)
    pnl_sum_rt = RT[(v, g)]["pnl"].sum()
    pnl_sum_daily = (res["daily"]["ret"] * res["daily"]["aum_start"]).sum()
    assert abs(pnl_sum_rt - pnl_sum_daily) < 1e-6, (v, g, pnl_sum_rt, pnl_sum_daily)
print("BLOCK-09 ok")
print(TLS[TLS.Grid == "g30"].to_string(index=False))
''')

# ============================================================ BLOCK-10
md('''## BLOCK-10 图形（Fig 1-7）

Fig1 噪声带概念；Fig2 案例日（2022-01-31 多 / 2022-04-29 空，510300 同日历日复刻）；
Fig3 权益 A vs B&H；Fig4/Fig5 案例 2022-01-20（变体 A vs B 止损对比）；Fig6 权益 A/B vs B&H；Fig7 权益 A/B/C vs B&H。
日内图横轴为**交易分钟序号**（午休 11:30/13:01 以竖虚线标注、不占轴长，DEC-011）；VWAP 为 g30 网格口径步进线（DEC-009）；
**噪声带 UB/LB 按 1 分钟全分辨率绘制**（DEC-012：σ/UB/LB 本就在 240 个 1 分钟标签上计算，图形不再按检查点抽样连线；
交易决策仍只在网格时点发生，引擎行为不变）。
输出：`10_fig*.png` 及 `10_*_data.csv`。''')

code('''# BLOCK-10 图形（CD-002：交易分钟横轴、午休剔除，DEC-011；CD-003：噪声带 1 分钟全分辨率，DEC-012）
XMIN = np.arange(len(PRICE_LABELS))                # 交易分钟序号 0..239（09:31..15:00，午休不占轴）
TICKS = ["09:31", "10:00", "10:30", "11:00", "11:30", "13:30", "14:00", "14:30", "15:00"]
LUNCH_X = PPos["11:30"] + 0.5                      # 11:30 与 13:01 在序号轴上相邻

def intraday_axis(ax):
    ax.set_xticks([PPos[t] for t in TICKS])
    ax.set_xticklabels(TICKS, fontsize=8)
    ax.axvline(LUNCH_X, color="gray", ls=":", lw=1.0)
    ax.set_xlim(-2, len(PRICE_LABELS) + 1)
    ax.set_xlabel("Time of day (lunch break removed; dotted line = 11:30 | 13:01)", fontsize=8)


def bands_1m(di, vm=VOL_MULT, lookback=LOOKBACK):
    return bands_for(di, vm, lookback)               # 全 240 个 1 分钟标签的 UB/LB（DEC-012）


def vwap_step_g30(di):
    sigs = [SIG_BAR.get(t, t) for t in GRIDS["g30"]] + ["15:00"]
    return (np.array([PPos[s] for s in sigs]),
            np.array([VWAP_G["g30"][di, IDX[s]] for s in sigs]))


def vwap_ffill_g30(di):
    return pd.Series(VWAP_G["g30"][di]).ffill().to_numpy()[1:]


def plot_day(ax, di, title, trades=None, show_vwap=True):
    ax.plot(XMIN, C_m[di, 1:], color="black", lw=1.2, label="510300 price")
    ub1m, lb1m = bands_1m(di)                        # DEC-012：1 分钟全分辨率，非检查点步进
    ax.plot(XMIN, ub1m, color="tab:red", lw=1.0, label="UB (1-min)")
    ax.plot(XMIN, lb1m, color="tab:green", lw=1.0, label="LB (1-min)")
    ax.fill_between(XMIN, lb1m, ub1m, alpha=0.15, color="gray", label="Noise area")
    if show_vwap:
        xv, vv = vwap_step_g30(di)
        ax.step(xv, vv, where="post", color="tab:blue", lw=1.0, ls="--", label="VWAP (g30 grid)")
    if trades is not None and len(trades):
        for r in trades.itertuples():
            x = PPos[r.exec_time]
            mk = "^" if r.side == "买入" else "v"
            c = "tab:red" if r.side == "买入" else "tab:green"
            ax.scatter([x], [r.price], marker=mk, color=c, s=55, zorder=5)
    ax.set_title(title, fontsize=10)
    intraday_axis(ax)
    ax.legend(fontsize=7, loc="best")
    ax.grid(alpha=0.25)


def nearest_di(d):
    ts = pd.Timestamp(d)
    if ts in day_pos:
        return day_pos[ts], d
    nxt = days[days.searchsorted(ts)]
    return day_pos[nxt], f"{d}(A-share closed) -> {nxt.date()}"


# Fig 1 概念图（2022-01-31；A 股春节休市 → 顺延至 2022-02-07）
di_f1, lab_f1 = nearest_di("2022-01-31")
fig, ax = plt.subplots(figsize=(9, 4.5))
plot_day(ax, di_f1, f"Fig1 Noise-area concept (510300, {lab_f1})")
fig.tight_layout()
fig.savefig(OUT / "10_fig1_concept.png")
plt.close(fig)
pd.DataFrame({"minute_idx": XMIN, "time": PRICE_LABELS, "close": C_m[di_f1, 1:],
              "sigma": SIGMA[LOOKBACK][di_f1],
              "UB": bands_1m(di_f1)[0], "LB": bands_1m(di_f1)[1],
              "vwap_g30": vwap_ffill_g30(di_f1)}).to_csv(OUT / "10_fig1_data.csv", index=False)

# Fig 2 两个案例日（变体 A g30 成交标记；同日历日复刻，遇 A 股休市顺延）
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
for ax, d in zip(axes, ["2022-01-31", "2022-04-29"]):
    di, lab = nearest_di(d)
    tr_d = RUNS[("A", "g30")]["trades"]
    plot_day(ax, di, f"Fig2 case {lab} (variant A trades)",
             trades=tr_d[tr_d.date == days[di]])
fig.tight_layout()
fig.savefig(OUT / "10_fig2_case_days.png")
plt.close(fig)
fig2_rows = []
for d in ["2022-01-31", "2022-04-29"]:
    di, lab = nearest_di(d)
    vw_ff = vwap_ffill_g30(di)
    ub_d, lb_d = bands_1m(di)
    sg_d = SIGMA[LOOKBACK][di]
    for k, lab2 in enumerate(PRICE_LABELS):
        fig2_rows.append((lab, XMIN[k], lab2, C_m[di, k + 1], sg_d[k], ub_d[k], lb_d[k], vw_ff[k]))
pd.DataFrame(fig2_rows, columns=["case", "minute_idx", "time", "close", "sigma", "UB", "LB",
                                 "vwap_g30"]).to_csv(OUT / "10_fig2_data.csv", index=False)

# Fig 3 权益 A vs B&H
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(days, RUNS[("A", "g30")]["equity"]["nav"], label="Variant A (opp band)", lw=1.2)
ax.plot(days, bh_nav, label="B&H 510300", lw=1.0)
ax.set_yscale("log")
ax.legend()
ax.grid(alpha=0.3)
ax.set_title("Fig3 Equity: Variant A vs B&H (log scale, g30)")
fig.tight_layout()
fig.savefig(OUT / "10_fig3_equity_oppband.png")
plt.close(fig)
pd.DataFrame({"date": days, "nav_A": RUNS[("A", "g30")]["equity"]["nav"],
              "nav_BH": bh_nav}).to_csv(OUT / "10_fig3_data.csv", index=False)

# Fig 4/5 案例 2022-01-20：变体 A vs 变体 B 止损
di_f4 = day_pos[pd.Timestamp("2022-01-20")]
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
plot_day(axes[0], di_f4, "Fig4 2022-01-20 variant A (opp-band stop)",
         trades=RUNS[("A", "g30")]["trades"][lambda x: x.date == pd.Timestamp("2022-01-20")])
plot_day(axes[1], di_f4, "Fig5 2022-01-20 variant B (max(UB,VWAP) stop)",
         trades=RUNS[("B", "g30")]["trades"][lambda x: x.date == pd.Timestamp("2022-01-20")])
fig.tight_layout()
fig.savefig(OUT / "10_fig4_case_20220120.png")
plt.close(fig)
fig, ax = plt.subplots(figsize=(9, 4.5))
plot_day(ax, di_f4, "Fig5 stop comparison 2022-01-20 (A red marks / B blue marks)")
trA = RUNS[("A", "g30")]["trades"]
trB = RUNS[("B", "g30")]["trades"]
for r in trA[trA.date == pd.Timestamp("2022-01-20")].itertuples():
    ax.scatter([PPos[r.exec_time]], [r.price], marker="o", color="tab:red", s=45, zorder=5)
for r in trB[trB.date == pd.Timestamp("2022-01-20")].itertuples():
    ax.scatter([PPos[r.exec_time]], [r.price], marker="x", color="tab:blue", s=45, zorder=6)
fig.tight_layout()
fig.savefig(OUT / "10_fig5_stops_20220120.png")
plt.close(fig)
fig5_rows = []
for r in trA[trA.date == pd.Timestamp("2022-01-20")].itertuples():
    fig5_rows.append(("A", PPos[r.exec_time], r.exec_time, r.price, r.side))
for r in trB[trB.date == pd.Timestamp("2022-01-20")].itertuples():
    fig5_rows.append(("B", PPos[r.exec_time], r.exec_time, r.price, r.side))
pd.DataFrame(fig5_rows, columns=["variant", "minute_idx", "time", "price", "side"]).to_csv(
    OUT / "10_fig5_data.csv", index=False)
pd.DataFrame({"minute_idx": XMIN, "time": PRICE_LABELS, "close": C_m[di_f4, 1:],
              "sigma": SIGMA[LOOKBACK][di_f4],
              "UB": bands_1m(di_f4)[0], "LB": bands_1m(di_f4)[1],
              "vwap_g30": vwap_ffill_g30(di_f4)}).to_csv(OUT / "10_fig4_data.csv", index=False)

# Fig 6 权益 A/B vs B&H
fig, ax = plt.subplots(figsize=(9, 4.5))
for v, c in [("A", "tab:orange"), ("B", "tab:blue")]:
    ax.plot(days, RUNS[(v, "g30")]["equity"]["nav"], label=f"Variant {v}", lw=1.1, color=c)
ax.plot(days, bh_nav, label="B&H 510300", lw=1.0, color="black")
ax.set_yscale("log")
ax.legend()
ax.grid(alpha=0.3)
ax.set_title("Fig6 Equity: Variants A, B vs B&H (log, g30)")
fig.tight_layout()
fig.savefig(OUT / "10_fig6_equity_ab.png")
plt.close(fig)
pd.DataFrame({"date": days, "nav_A": RUNS[("A", "g30")]["equity"]["nav"],
              "nav_B": RUNS[("B", "g30")]["equity"]["nav"], "nav_BH": bh_nav}
             ).to_csv(OUT / "10_fig6_data.csv", index=False)

# Fig 7 权益 A/B/C vs B&H
fig, ax = plt.subplots(figsize=(9, 4.5))
for v, c in [("A", "tab:orange"), ("B", "tab:blue"), ("C", "tab:red")]:
    ax.plot(days, RUNS[(v, "g30")]["equity"]["nav"], label=f"Variant {v}", lw=1.1, color=c)
ax.plot(days, bh_nav, label="B&H 510300", lw=1.0, color="black")
ax.set_yscale("log")
ax.legend()
ax.grid(alpha=0.3)
ax.set_title("Fig7 Equity: Variants A, B, C vs B&H (log, g30)")
fig.tight_layout()
fig.savefig(OUT / "10_fig7_equity_abc.png")
plt.close(fig)
pd.DataFrame({"date": days, "nav_A": RUNS[("A", "g30")]["equity"]["nav"],
              "nav_B": RUNS[("B", "g30")]["equity"]["nav"],
              "nav_C": RUNS[("C", "g30")]["equity"]["nav"], "nav_BH": bh_nav}
             ).to_csv(OUT / "10_fig7_data.csv", index=False)
print("BLOCK-10 ok | figures 1-7 saved")
''')

# ============================================================ BLOCK-11
md('''## BLOCK-11 Figure 8 波动机制（σ_SPY 代理）

无 VIX 数据（DEC-006）：以 σ_SPY,t（14 日日收益 std，开盘前可得）分档，
各门槛以上交易日的变体 C（g30）日收益 Sharpe。输出：`11_vol_regime_sharpe.csv`、`11_fig8_vol_regime.png`。''')

code('''# BLOCK-11 波动机制
dlC = RUNS[("C", "g30")]["daily"]
thr_list = [0.0, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.025, 0.03]
rows = []
for thr in thr_list:
    m = (dlC["lev"].notna()) & (dlC["traded"] == 1) & (pd.Series(sigma14_v, index=days).reindex(dlC.date).to_numpy() >= thr)
    r = dlC.loc[m, "ret"].to_numpy()
    sd = r.std(ddof=1) if len(r) > 1 else np.nan
    rows.append({"sigma_threshold": thr, "days": int(m.sum()),
                 "sharpe": r.mean() / sd * math.sqrt(252.0) if (sd and sd > 0) else np.nan,
                 "avg_bps": float(r.mean()) * 1e4 if len(r) else np.nan})
VR = pd.DataFrame(rows)
VR.to_csv(OUT / "11_vol_regime_sharpe.csv", index=False)
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.plot(VR["sigma_threshold"] * 100, VR["sharpe"], marker="o")
ax.set_xlabel("sigma_SPY,t threshold (%)")
ax.set_ylabel("Sharpe (traded days above threshold)")
ax.set_title("Fig8 Volatility regime: Sharpe by sigma_SPY threshold (variant C, g30)")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "11_fig8_vol_regime.png")
plt.close(fig)
print("BLOCK-11 ok")
print(VR.to_string(index=False))
''')

# ============================================================ BLOCK-12
md('''## BLOCK-12 Table 5 八种日内形态（t−1 判定，无前视）

形态由 t−1 及以前日频 OHLC 判定，统计 t 日变体 C（g30）traded-day 收益。
输出：`12_daily_patterns.csv`。''')

code('''# BLOCK-12 日内形态
H_d = s["high"].reindex(days).to_numpy()
L_d = s["low"].reindex(days).to_numpy()
O_d = s["open"].reindex(days).to_numpy()
C_d = s["close"].reindex(days).to_numpy()
rng = pd.Series(H_d - L_d, index=days)
h_s = pd.Series(H_d, index=days)
l_s = pd.Series(L_d, index=days)
o_s = pd.Series(O_d, index=days)
c_s = pd.Series(C_d, index=days)

is_nr4 = (rng == rng.rolling(4).min())
is_nr7 = (rng == rng.rolling(7).min())
is_id = (h_s < h_s.shift(1)) & (l_s > l_s.shift(1))
is_od = (h_s > h_s.shift(1)) & (l_s < l_s.shift(1))
is_tri = (h_s < h_s.shift(1)) & (h_s < h_s.shift(2)) & (l_s > l_s.shift(1)) & (l_s > l_s.shift(2))
pos_o = (o_s - l_s) / rng.replace(0, np.nan)
pos_c = (c_s - l_s) / rng.replace(0, np.nan)
rng_ok = rng > rng.rolling(14).mean()
is_trend = ((pos_o <= 0.15) & (pos_c >= 0.85) & rng_ok) | ((pos_o >= 0.85) & (pos_c <= 0.15) & rng_ok)
is_bigtail = ((pos_o >= 0.75) & (pos_c >= 0.75)) | ((pos_o <= 0.25) & (pos_c <= 0.25))
is_strong = pos_c >= 0.90
is_weak = pos_c <= 0.10

PATTERNS = {"NR4": is_nr4, "NR7": is_nr7, "ID": is_id, "OD": is_od, "Triangle": is_tri,
            "TrendDay": is_trend, "BigTail": is_bigtail, "StrongClose": is_strong, "WeakClose": is_weak}

# 手工验证 2 日 NR4 / ID
for d in ["2020-03-05", "2023-08-28"]:
    i = days.get_loc(pd.Timestamp(d))
    manual_nr4 = (rng.iloc[i - 1] == rng.iloc[i - 4:i].min())
    assert bool(is_nr4.shift(1).iloc[i]) == bool(manual_nr4), (d, "NR4")
    manual_id = (H_d[i - 1] < H_d[i - 2]) and (L_d[i - 1] > L_d[i - 2])
    assert bool(is_id.shift(1).iloc[i]) == manual_id, (d, "ID")

retC = pd.Series(dlC["ret"].to_numpy(), index=days)
traded = pd.Series(dlC["traded"].to_numpy(), index=days) == 1
rows = []
def pat_stats(mask, name):
    m = mask & traded & retC.notna()
    r = retC[m].to_numpy()
    n = len(r)
    sd = r.std(ddof=1) if n > 1 else np.nan
    rows.append({"Pattern": name, "Observations": n,
                 "AvgPnLBps": float(r.mean()) * 1e4 if n else np.nan,
                 "tstat": float(r.mean() / (sd / math.sqrt(n))) if (sd and sd > 0) else np.nan,
                 "HitRatio": float((r > 0).mean()) if n else np.nan,
                 "Sharpe": float(r.mean() / sd * math.sqrt(252.0)) if (sd and sd > 0) else np.nan})

pat_stats(pd.Series(True, index=days), "Unconditional")
for name, ser in PATTERNS.items():
    pat_stats(ser.shift(1).fillna(False).astype(bool), name)
PAT = pd.DataFrame(rows)
PAT.to_csv(OUT / "12_daily_patterns.csv", index=False)
print("BLOCK-12 ok")
print(PAT.to_string(index=False))
''')

# ============================================================ BLOCK-13
md('''## BLOCK-13 Table 6 星期效应

变体 C（g30）traded-day 日收益按星期分组。输出：`13_day_of_week.csv`。''')

code('''# BLOCK-13 星期效应
dow = pd.Series(days.dayofweek, index=days)
rows = []
for k, name in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]):
    m = (dow == k) & traded & retC.notna()
    r = retC[m].to_numpy()
    n = len(r)
    sd = r.std(ddof=1) if n > 1 else np.nan
    rows.append({"Weekday": name, "Observations": n,
                 "AvgPnLBps": float(r.mean()) * 1e4 if n else np.nan,
                 "tstat": float(r.mean() / (sd / math.sqrt(n))) if (sd and sd > 0) else np.nan,
                 "HitRatio": float((r > 0).mean()) if n else np.nan,
                 "Sharpe": float(r.mean() / sd * math.sqrt(252.0)) if (sd and sd > 0) else np.nan})
DOW = pd.DataFrame(rows)
assert DOW["Observations"].sum() == int(traded.sum())
DOW.to_csv(OUT / "13_day_of_week.csv", index=False)
print("BLOCK-13 ok")
print(DOW.to_string(index=False))
''')

# ============================================================ BLOCK-14
md('''## BLOCK-14 Figure 9 波动乘数 VM 扫描

VM ∈ {0.2, 0.4, …, 2.4} 共 12 档，每档全量重跑变体 C（g30）。VM=1 与 BLOCK-08 锚点勾稽。
输出：`14_vm_sweep.csv`、`14_fig9_vm_sweep.png`。''')

code('''# BLOCK-14 VM 扫描
vm_list = [round(0.2 * k, 1) for k in range(1, 13)]
rows = []
for vm in vm_list:
    res = run_backtest("g30", "band_vwap", dyn_lev=True, vm=vm, tag=f"VM{vm}")
    st = perf_stats(res["daily"]["ret"], res["daily"]["aum_end"])
    rows.append({"VM": vm, "Sharpe": st["Sharpe"], "TotalReturn": st["TotalReturn"],
                 "IRR": st["IRR"], "MDD": st["MDD"], "N_Exec": len(res["trades"])})
VM_SW = pd.DataFrame(rows)
anchor = VM_SW[np.isclose(VM_SW.VM, 1.0)].iloc[0]
base = SUMMARY[(SUMMARY.Variant == "C") & (SUMMARY.Grid == "g30")].iloc[0]
assert abs(anchor["TotalReturn"] - base["TotalReturn"]) < 1e-9, (anchor["TotalReturn"], base["TotalReturn"])
VM_SW.to_csv(OUT / "14_vm_sweep.csv", index=False)
fig, ax = plt.subplots(figsize=(9, 4.2))
x = np.arange(len(VM_SW))
ax.bar(x - 0.2, VM_SW["Sharpe"], width=0.4, label="Sharpe")
ax2 = ax.twinx()
ax2.bar(x + 0.2, VM_SW["TotalReturn"], width=0.4, color="tab:orange", label="Total Return")
ax.set_xticks(x)
ax.set_xticklabels(VM_SW["VM"])
ax.set_xlabel("Volatility Multiplier (VM)")
ax.set_title("Fig9 VM sweep (variant C, g30)")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "14_fig9_vm_sweep.png")
plt.close(fig)
print("BLOCK-14 ok | VM=1 anchor matched")
print(VM_SW.to_string(index=False))
''')

# ============================================================ BLOCK-15
md('''## BLOCK-15 §4.5 RSI(5) 回归

$RetMom_t(bps)=\\alpha+\\beta\\cdot RSI_{SPY,t-1}+\\varepsilon$；RSI 用 510300 日收盘，
**Wilder 平滑**（ewm alpha=1/5, adjust=False, min_periods=5）；自变量 t−1 收盘可得；
因变量变体 C（g30）日收益 bps（全样本日，无交易=0）。论文锚点 β=−3.25, p=0.001（SPY 口径）。
另附**零成本口径 A/B/C 回归**（DEC-014，用户 2026-10-19）：剔除费用后检验 RSI 与策略毛收益的关系。
输出：`15_rsi_regression.csv`、`15_rsi_regression_zero_cost.csv`、`15_rsi_zero_cost_daily.csv`。''')

code('''# BLOCK-15 RSI 回归
close_full = dl_full.set_index("trade_date")["close"]
rsi_full = rsi_wilder(close_full, 5)
rsi_sample = rsi_full.reindex(days)
# 手工复算 3 日 RSI（Wilder）
for d in ["2020-07-06", "2023-04-10", "2025-06-24"]:
    i = dl_full.index[dl_full.trade_date == pd.Timestamp(d)][0]
    seg = close_full.iloc[:i + 1]
    dlt = seg.diff()
    up = dlt.clip(lower=0.0)
    dn = -dlt.clip(upper=0.0)
    au = up.iloc[1:6].mean()
    ad = dn.iloc[1:6].mean()
    for k in range(6, len(seg)):
        au = (au * 4 + up.iloc[k]) / 5.0
        ad = (ad * 4 + dn.iloc[k]) / 5.0
    manual = 100.0 - 100.0 / (1.0 + au / ad) if ad > 0 else 100.0
    assert abs(manual - rsi_full.iloc[i]) < 1e-9, (d, manual, rsi_full.iloc[i])

y_bps = retC.to_numpy() * 1e4
x_rsi = rsi_sample.shift(1).to_numpy()
reg = ols_stats(y_bps, x_rsi)
pd.DataFrame([{"alpha_bps": reg["alpha"], "beta": reg["beta"], "t_beta": reg["t_beta"],
               "p_beta": reg["p_beta"], "n": reg["n"], "r2": reg["r2"],
               "note": "RSI(5) Wilder on 510300 close; x=RSI(t-1); y=variant C g30 daily ret (bps)"}]
             ).to_csv(OUT / "15_rsi_regression.csv", index=False)
assert reg["n"] == int((~np.isnan(x_rsi)).sum())
print(f"BLOCK-15 ok | beta={reg['beta']:.3f} t={reg['t_beta']:.2f} p={reg['p_beta']:.4f} n={reg['n']}")

# DEC-014：零成本口径 A/B/C 的 RSI 回归（用户 2026-10-19；剔除费用影响的毛收益口径）
zc_rows = []
zc_daily = {"date": days, "rsi_lag1": x_rsi}
for v, mode, dl_ in [("A", "opp_band", False), ("B", "band_vwap", False), ("C", "band_vwap", True)]:
    res = run_backtest("g30", mode, dyn_lev=dl_, commission=0.0, slippage=0.0, tag=f"rsiz_{v}")
    yv = res["daily"]["ret"].to_numpy() * 1e4
    reg_v = ols_stats(yv, x_rsi)
    zc_rows.append({"variant": v, "cost": "zero", "alpha_bps": reg_v["alpha"],
                    "beta": reg_v["beta"], "t_beta": reg_v["t_beta"], "p_beta": reg_v["p_beta"],
                    "n": reg_v["n"], "r2": reg_v["r2"],
                    "note": "x=RSI(t-1); y=variant g30 zero-cost daily ret (bps), all days"})
    zc_daily[f"ret_{v}"] = res["daily"]["ret"].to_numpy()
ZC15 = pd.DataFrame(zc_rows)
assert (ZC15["n"] == reg["n"]).all()                      # 与净口径同一 n（同一掩码）
ZC15.to_csv(OUT / "15_rsi_regression_zero_cost.csv", index=False)
pd.DataFrame(zc_daily).to_csv(OUT / "15_rsi_zero_cost_daily.csv", index=False)
print(ZC15[["variant", "beta", "t_beta", "p_beta", "n", "r2"]].to_string(index=False))
''')

# ============================================================ BLOCK-16
md('''## BLOCK-16 Figure 10 成本敏感性

佣金率谱 {0, 0.005%, 0.01%, 0.02%, 0.03%} × 滑点 {0, 1, 2} tick 重跑变体 C（g30）。
另附**三变体零滑点万 1 对照**（DEC-013，g30）：A/B/C 在 commission=万1、slippage=0 下的完整指标。
输出：`16_cost_sensitivity.csv`、`16_cost_w1_zero_slip.csv`、`16_fig10_cost.png`。''')

code('''# BLOCK-16 成本敏感性
comm_list = [0.0, 0.00005, 0.0001, 0.0002, 0.0003]
slip_list = [0.0, 0.001, 0.002]
rows = []
for cm in comm_list:
    for sl in slip_list:
        res = run_backtest("g30", "band_vwap", dyn_lev=True, commission=cm, slippage=sl,
                           tag=f"cost_c{cm}_s{sl}")
        st = perf_stats(res["daily"]["ret"], res["daily"]["aum_end"])
        rows.append({"commission": cm, "slippage": sl, "TotalReturn": st["TotalReturn"],
                     "IRR": st["IRR"], "Sharpe": st["Sharpe"], "MDD": st["MDD"]})
COST = pd.DataFrame(rows)
zero = COST[(COST.commission == 0.0) & (COST.slippage == 0.0)].iloc[0]
print(f"zero-cost anchor: TR={zero['TotalReturn']:.2%} Sharpe={zero['Sharpe']:.3f}")
# 成本单调性：固定滑点，佣金升 → TR 不增
for sl in slip_list:
    sub = COST[COST.slippage == sl].sort_values("commission")["TotalReturn"].to_numpy()
    assert all(sub[i + 1] <= sub[i] + 1e-9 for i in range(len(sub) - 1)), sl
COST.to_csv(OUT / "16_cost_sensitivity.csv", index=False)
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for sl, mk in zip(slip_list, ["o", "s", "^"]):
    sub = COST[COST.slippage == sl].sort_values("commission")
    ax.plot(sub["commission"] * 1e4, sub["TotalReturn"], marker=mk, label=f"slippage {sl * 1000:.0f} tick(s) x0.001")
ax.axvline(1.0, color="gray", ls=":", lw=1)
ax.set_xlabel("Commission per side (bps)")
ax.set_ylabel("Total Return")
ax.set_title("Fig10 Cost sensitivity (variant C, g30)")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "16_fig10_cost.png")
plt.close(fig)
print("BLOCK-16 ok | monotonicity verified")
print(COST.to_string(index=False))

# DEC-013：三变体零滑点万1对照（g30；用户 2026-10-19 裁决）
W1Z_SPEC = [("A", "opp_band", False), ("B", "band_vwap", False), ("C", "band_vwap", True)]
w1z_rows = []
for v, mode, dl_ in W1Z_SPEC:
    res = run_backtest("g30", mode, dyn_lev=dl_, commission=0.0001, slippage=0.0,
                       tag=f"w1z_{v}")
    st = perf_stats(res["daily"]["ret"], res["daily"]["aum_end"])
    w1z_rows.append({"Variant": v, "commission": 0.0001, "slippage": 0.0,
                     "exec_rows": int(len(res["trades"])), **st})
W1Z = pd.DataFrame(w1z_rows)
# 勾稽：C 行须与成本谱中 (万1, 0 tick) 行一致（同一引擎路径）
c_spec = COST[(COST.commission.round(6) == 0.0001) & (COST.slippage == 0.0)].iloc[0]
c_w1z = W1Z[W1Z.Variant == "C"].iloc[0]
assert abs(c_w1z["TotalReturn"] - c_spec["TotalReturn"]) < 1e-9
assert abs(c_w1z["Sharpe"] - c_spec["Sharpe"]) < 1e-9
W1Z.to_csv(OUT / "16_cost_w1_zero_slip.csv", index=False)
print("W1Z (万1, 0 tick, g30):")
print(W1Z[["Variant", "TotalReturn", "IRR", "Vol", "Sharpe", "HitRatio", "MDD", "exec_rows"]]
      .to_string(index=False))
''')

# ============================================================ BLOCK-17
md('''## BLOCK-17 FAQ 扩展

Q4/Q24 月度收益表；Q5 多空腿权益；Q6 lookback 扫描；Q7 最差 10 季度；Q18 日内季节性；
Q19 空头 PnL ~ σ_SPY 回归；Q22 VWAP-only 止损；Q23 逐年每笔利润；Q12 扩展 ETF 简版。
输出：`17_*` 系列文件。''')

code('''# BLOCK-17.1 Q4/Q24 月度收益表（变体 C g30 + B&H）
dlC2 = dlC.copy()
dlC2["ym"] = dlC2["date"].dt.to_period("M")
m_strat = dlC2.groupby("ym")["ret"].apply(lambda x: (1 + x).prod() - 1)
m_bh = pd.Series(ret_v, index=days).groupby(days.to_period("M")).apply(lambda x: (1 + x).prod() - 1)
mt = pd.DataFrame({"strat": m_strat, "bh": m_bh})
mt["year"] = mt.index.year
mt["month"] = mt.index.month
piv = mt.pivot(index="year", columns="month", values="strat")
piv.columns = [f"M{m:02d}" for m in piv.columns]
piv["YTD"] = mt.groupby("year")["strat"].apply(lambda x: (1 + x).prod() - 1)
piv["BH_YTD"] = mt.groupby("year")["bh"].apply(lambda x: (1 + x).prod() - 1)
piv.to_csv(OUT / "17_monthly_table.csv")
assert len(mt) == len(days.to_period("M").unique())
print(f"Q4/Q24 monthly table: {len(mt)} months x years {piv.shape[0]}")

# BLOCK-17.2 Q5 多空腿权益
rtC = RT[("C", "g30")].copy()
rtC["date"] = pd.to_datetime(rtC["date"])
pnl_long = rtC[rtC.direction == "long"].groupby("date")["pnl"].sum()
pnl_short = rtC[rtC.direction == "short"].groupby("date")["pnl"].sum()
eq_long = INIT_CAPITAL + pnl_long.reindex(days).fillna(0.0).cumsum()
eq_short = INIT_CAPITAL + pnl_short.reindex(days).fillna(0.0).cumsum()
pd.DataFrame({"date": days, "eq_long": eq_long.to_numpy(), "eq_short": eq_short.to_numpy(),
              "eq_both": RUNS[("C", "g30")]["equity"]["aum_end"].to_numpy()}
             ).to_csv(OUT / "17_long_short_legs.csv", index=False)
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(days, eq_long, label="Long leg", lw=1.1)
ax.plot(days, eq_short, label="Short leg", lw=1.1)
ax.plot(days, RUNS[("C", "g30")]["equity"]["aum_end"], label="Both", lw=1.1, color="black")
ax.set_yscale("log")
ax.legend()
ax.grid(alpha=0.3)
ax.set_title("Q5 Long/Short leg equity (variant C, g30)")
fig.tight_layout()
fig.savefig(OUT / "17_long_short_legs.png")
plt.close(fig)
print(f"Q5 legs: long end={eq_long.iloc[-1]:,.0f} short end={eq_short.iloc[-1]:,.0f}")

# BLOCK-17.3 Q6 lookback 扫描（噪声带 lookback；仓位 sigma14 固定 14）
lb_list = [5, 10, 14, 20, 25, 30, 60, 90]
rows = []
for lbk in lb_list:
    res = run_backtest("g30", "band_vwap", dyn_lev=True, lookback=lbk, tag=f"LB{lbk}")
    st = perf_stats(res["daily"]["ret"], res["daily"]["aum_end"])
    rows.append({"lookback": lbk, "TotalReturn": st["TotalReturn"], "IRR": st["IRR"],
                 "Vol": st["Vol"], "Sharpe": st["Sharpe"], "MDD": st["MDD"],
                 "N_Exec": len(res["trades"])})
LB_SW = pd.DataFrame(rows)
a14 = LB_SW[LB_SW.lookback == 14].iloc[0]
assert abs(a14["TotalReturn"] - base["TotalReturn"]) < 1e-9
LB_SW.to_csv(OUT / "17_lookback_sweep.csv", index=False)
print("Q6 lookback sweep:")
print(LB_SW.to_string(index=False))

# BLOCK-17.4 Q7 最差 10 季度（510300 B&H 季度收益）
q_bh = pd.Series(ret_v, index=days).groupby(days.to_period("Q")).apply(lambda x: (1 + x).prod() - 1)
q_strat = dlC2.groupby(dlC2["date"].dt.to_period("Q"))["ret"].apply(lambda x: (1 + x).prod() - 1)
qt = pd.DataFrame({"bh": q_bh, "strat": q_strat}).sort_values("bh")
worst10 = qt.head(10).reset_index()
worst10.columns = ["quarter", "bh_ret", "strat_ret"]
worst10.to_csv(OUT / "17_worst_quarters.csv", index=False)
print("Q7 worst 10 quarters (BH) vs strategy:")
print(worst10.to_string(index=False))

# BLOCK-17.5 Q18 日内季节性（按入场决策时点聚合平均每笔 PnL）
ent = rtC.copy()
sea = ent.groupby("entry_time").agg(n=("pnl", "size"), avg_pnl_bps=("ret_on_notional", lambda x: x.mean() * 1e4),
                                    avg_pnl_per_share=("pnl_per_share", "mean")).reset_index()
sea["order"] = sea["entry_time"].map(label_key)
sea = sea.sort_values("order").drop(columns="order")
sea.to_csv(OUT / "17_intraday_seasonality.csv", index=False)
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.bar(sea["entry_time"], sea["avg_pnl_bps"])
ax.set_title("Q18 Intraday seasonality: avg round-trip PnL (bps) by entry decision time")
ax.set_ylabel("bps on notional")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "17_intraday_seasonality.png")
plt.close(fig)
print("Q18 seasonality:")
print(sea.to_string(index=False))

# BLOCK-17.6 Q19 空头整趟 PnL(bps) ~ 当日 sigma_SPY 回归
sh = rtC[rtC.direction == "short"].copy()
sh["sig"] = pd.Series(sigma14_v, index=days).reindex(sh["date"]).to_numpy()
reg19 = ols_stats(sh["ret_on_notional"].to_numpy() * 1e4, sh["sig"].to_numpy())
pd.DataFrame([{"alpha_bps": reg19["alpha"], "beta": reg19["beta"], "t_beta": reg19["t_beta"],
               "p_beta": reg19["p_beta"], "n": reg19["n"], "r2": reg19["r2"],
               "note": "short round-trip PnL(bps) ~ sigma_SPY,t (VIX proxy)"}]
             ).to_csv(OUT / "17_short_pnl_vol_regression.csv", index=False)
print(f"Q19 short PnL ~ sigma_SPY: beta={reg19['beta']:.1f} p={reg19['p_beta']:.3f} n={reg19['n']}")

# BLOCK-17.7 Q22 VWAP-only 止损变体
res_vw = run_backtest("g30", "vwap_only", dyn_lev=True, tag="Q22_vwap_only")
st_vw = perf_stats(res_vw["daily"]["ret"], res_vw["daily"]["aum_end"])
st_vw["N_Exec"] = len(res_vw["trades"])
pd.DataFrame([st_vw]).to_csv(OUT / "17_vwap_only_stats.csv", index=False)
print(f"Q22 VWAP-only: TR={st_vw['TotalReturn']:.2%} Sharpe={st_vw['Sharpe']:.3f} exec={st_vw['N_Exec']} "
      f"(vs band_vwap exec={len(RUNS[('C', 'g30')]['trades'])})")

# BLOCK-17.8 Q23 逐年平均每笔 PnL/Share
rtC["year"] = rtC["date"].dt.year
py = rtC.groupby("year").agg(avg_pnl_per_share=("pnl_per_share", "mean"),
                             n_trades=("pnl", "size")).reset_index()
py.to_csv(OUT / "17_profit_per_share_by_year.csv", index=False)
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.bar(py["year"].astype(str), py["avg_pnl_per_share"])
ax.set_title("Q23 Avg profit per share by year (variant C, g30)")
ax.set_ylabel("yuan / share")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "17_profit_per_share_by_year.png")
plt.close(fig)
print("Q23 by year:")
print(py.to_string(index=False))
''')

code('''# BLOCK-17.9 Q12 扩展 ETF（510500/159915/588000，变体 C g30 简版）
# 复用主引擎：构建与各标的同构的数据上下文，临时替换模块级变量后运行，跑完恢复。
# 注：扩展标的未构建分钟级 tradability（BUYABLE/SELLABLE 全 True），仅作汇总指标参考。
CTX_KEYS = ["days", "n_days", "C_l", "O_l", "VW_G_l", "BUY_l", "SELL_l",
            "s14_l", "do_l", "pc_l", "SIGMA", "day_pos"]


def build_ext_ctx(tag):
    mn2 = pd.read_parquet(EXT_DIR / f"minute_bars_{tag}.parquet")
    mn2 = mn2[(mn2.trade_date >= SAMPLE_START) & (mn2.trade_date <= SAMPLE_END)].sort_values("trade_time")
    assert set(mn2.hhmm.unique()) <= set(LABELS)
    days2 = pd.DatetimeIndex(sorted(mn2.trade_date.unique()))

    def to_mat2(col):
        piv = mn2.pivot(index="trade_date", columns="hhmm", values=col)
        return piv.reindex(index=days2, columns=LABELS).to_numpy(dtype=float)

    O2, C2, V2, A2 = to_mat2("open"), to_mat2("close"), to_mat2("vol"), to_mat2("amount")
    fv = np.argmax(~np.isnan(O2), axis=1)
    do2 = np.where(np.isnan(O2[:, IDX["09:30"]]), O2[np.arange(len(days2)), fv], O2[:, IDX["09:30"]])
    dl2 = pd.read_csv(EXT_DIR / f"daily_{tag}.csv", parse_dates=["trade_date"]).sort_values("trade_date")
    dl2["ret"] = dl2["pct_chg"] / 100.0
    dl2["sigma14"] = dl2["ret"].rolling(LOOKBACK).std(ddof=1).shift(1)
    s2 = dl2.set_index("trade_date")
    MOVE2 = np.abs(C2[:, 1:] / do2[:, None] - 1.0)
    SIG2 = {LOOKBACK: pd.DataFrame(MOVE2).rolling(LOOKBACK).mean().shift(1).to_numpy()}
    n2 = len(days2)
    # CD-002：外部品种 VWAP 同样按 g30 决策间隔 bar 口径（DEC-009）
    cols30 = GRID_BARS["g30"]
    pv2 = np.zeros((n2, len(cols30)))
    vv2 = np.zeros((n2, len(cols30)))
    for k, (slab, c0, c1) in enumerate(cols30):
        close_k = C2[:, c1]
        vol_k = np.nansum(np.where(np.isnan(V2[:, c0:c1 + 1]), 0.0, V2[:, c0:c1 + 1]), axis=1)
        bad = np.isnan(close_k)
        pv2[:, k] = np.where(bad, 0.0, close_k * vol_k)
        vv2[:, k] = np.where(bad, 0.0, vol_k)
    cspv2 = np.cumsum(pv2, axis=1)
    csvv2 = np.cumsum(vv2, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        vwg2 = np.where(csvv2 > 0, cspv2 / csvv2, np.nan)
    VW2 = np.full((n2, n_lab), np.nan)
    for k, (slab, c0, c1) in enumerate(cols30):
        VW2[:, c1] = vwg2[:, k]
    buy2 = np.ones((n2, n_lab), dtype=bool).tolist()
    return {"days": days2, "n_days": n2, "C_l": C2.tolist(), "O_l": O2.tolist(),
            "VW_G_l": {"g30": VW2.tolist()}, "BUY_l": buy2, "SELL_l": [row[:] for row in buy2],
            "s14_l": s2["sigma14"].reindex(days2).to_numpy().tolist(),
            "do_l": do2.tolist(), "pc_l": s2["pre_close"].reindex(days2).to_numpy().tolist(),
            "SIGMA": SIG2, "day_pos": {d: i for i, d in enumerate(days2)}}


rows = []
for tag, nm in [("510500_SH", "510500.SH 中证500ETF"), ("159915_SZ", "159915.SZ 创业板ETF"),
                ("588000_SH", "588000.SH 科创50ETF")]:
    ctx = build_ext_ctx(tag)
    saved = {k: globals()[k] for k in CTX_KEYS}
    globals().update(ctx)
    try:
        res = run_backtest("g30", "band_vwap", dyn_lev=True, tag=f"Q12_{tag}")
    finally:
        globals().update(saved)
    st = perf_stats(res["daily"]["ret"], res["daily"]["aum_end"])
    st.update({"ETF": nm, "first_day": str(ctx["days"][0].date()), "days": int(ctx["n_days"]),
               "N_Exec": len(res["trades"])})
    rows.append(st)
    print(f"Q12 {nm}: days={ctx['n_days']} TR={st['TotalReturn']:.2%} Sharpe={st['Sharpe']:.3f}")
Q12 = pd.DataFrame(rows)[["ETF", "first_day", "days", "N", "TotalReturn", "IRR", "Vol",
                          "Sharpe", "HitRatio", "MDD", "N_Exec"]]
Q12.to_csv(OUT / "17_other_etfs.csv", index=False)
# 恢复后主上下文自检：主标的权益未变
assert abs(RUNS[("C", "g30")]["equity"]["nav"].iloc[-1] - (dlC["aum_end"].iloc[-1] / INIT_CAPITAL)) < 1e-12
print("Q12 done, main context restored")
''')

# ============================================================ BLOCK-18
md('''## BLOCK-18 标准交易流水与 A 股约束量化

- `trade_record.csv`：变体 C（g30）全部成交，前八列固定表头 + 审计列（UTF-8）
- 逐笔核验 tradability（可买/可卖、涨跌停范围、封板）；运行官方 validate_trade_record.py（≥3 探针：普通时点、15:00、涨停封板分钟）
- 底仓 T+0 可执行性量化：杠杆/名义本金分布 → 所需底仓+现金缓冲倍数；无底仓 T+1 对照
输出：`trade_record.csv`、`18_ashare_constraints.json`、`18_trade_validation.json`。''')

code('''# BLOCK-18 交易流水 + 官方校验 + A股约束量化
trC = RUNS[("C", "g30")]["trades"].copy()
rec = pd.DataFrame({
    "交易日期": pd.to_datetime(trC["date"]).dt.strftime("%Y%m%d"),
    "交易时间": trC["exec_time"].str.replace(":", ""),
    "股票代码": TS_CODE,
    "股票名称": TS_NAME,
    "交易价格": trC["price"].round(3),
    "交易数量": trC["shares"].astype(int),
    "交易方向": trC["side"],
    "交易标识": [f"{RUN_ID}-C30-{i:06d}" for i in range(1, len(trC) + 1)],
    "信号时间": trC["decision_time"],
    "止损类型": trC["reason"].replace("", "ENTRY"),
    "佣金": trC["commission"].round(4),
    "滑点": trC["slippage_cost"].round(4),
    "费用合计": trC["cost"].round(4),
    "杠杆": trC["lev"].round(4),
    "策略变体": "C(band_vwap+dynamic,g30)",
    "run_id": RUN_ID,
})
assert rec["交易标识"].is_unique
assert (rec["交易数量"] % 100 == 0).all() and (rec["交易数量"] > 0).all()
rec.to_csv(ROOT / "trade_record.csv", index=False, encoding="utf-8")

# 逐笔可交易性核验（含 15:00 强平）
chk = rec.merge(trad[["交易日期", "交易时间", "可买", "可卖", "涨停价", "跌停价", "涨停封板", "跌停封板", "是否有成交"]],
                on=["交易日期", "交易时间"], how="left")
assert chk["可买"].notna().all(), "存在 tradability 缺失的成交时点"
is_buy = chk["交易方向"] == "买入"
viol_buy = int(((chk["可买"] != 1) & is_buy).sum())
viol_sell = int(((chk["可卖"] != 1) & ~is_buy).sum())
viol_px = int(((chk["交易价格"] > chk["涨停价"] + 1e-9) | (chk["交易价格"] < chk["跌停价"] - 1e-9)).sum())
viol_seal = int(((chk["涨停封板"] == 1) & is_buy).sum() + ((chk["跌停封板"] == 1) & ~is_buy).sum())
viol_act = int((chk["是否有成交"] != 1).sum())
assert viol_buy == 0 and viol_sell == 0 and viol_px == 0 and viol_seal == 0 and viol_act == 0, \
    (viol_buy, viol_sell, viol_px, viol_seal, viol_act)
print(f"tradability 核验: {len(chk)} 笔全部合规 (buy/sell/price/seal violations = 0)")

# 官方校验器（>=3 探针：普通时点、15:00 强平时点、涨停封板分钟）
seal_row = trad[trad["涨停封板"] == 1].iloc[0]
probes = [f"{TS_CODE},{rec['交易日期'].iloc[0]},{rec['交易时间'].iloc[0]}",
          f"{TS_CODE},{rec[rec['交易时间'] == '1500']['交易日期'].iloc[0]},1500",
          f"{TS_CODE},{seal_row['交易日期']},{seal_row['交易时间']}"]
validator = ROOT.parent / ".github" / "harness" / "validators" / "validate_trade_record.py"
cmd = [sys.executable, str(validator), "--trades", str(ROOT / "trade_record.csv"),
       "--tradability", str(PROC / "tradability.csv")]
for p_ in probes:
    cmd += ["--probe", p_]
cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
val_out = {"returncode": cp.returncode, "probes": probes,
           "stdout_tail": cp.stdout[-2000:], "stderr_tail": cp.stderr[-1000:]}
dump_json(val_out, "18_trade_validation.json")
print("validate_trade_record returncode:", cp.returncode)
print(cp.stdout[-600:])
assert cp.returncode == 0, "official trade-record validator FAILED"

# A 股约束量化（底仓 T+0 可执行性）
lev_s = dlC["lev"].dropna()
rtC2 = RT[("C", "g30")]
constraints = {
    "mode": "EXECUTABLE_WITH_INVENTORY_T0",
    "assumption": ("用户 2026-10-04 裁决：账户已持有足额底仓与现金缓冲；多头腿先买(现金)后卖(旧份额)、"
                   "空头腿先卖(底仓)后买(资金回笼)，日内均可合法闭合；不使用融券"),
    "buffer_requirement": {
        "long_leg": "现金缓冲 >= 当日名义本金 = lev x AUM",
        "short_leg": "底仓缓冲(份额) >= 当日名义本金 = lev x AUM",
        "note": "缓冲倍数 = 当日杠杆；下表给出杠杆分布"},
    "lev_distribution": {
        "mean": float(lev_s.mean()), "median": float(lev_s.median()),
        "p95": float(lev_s.quantile(0.95)), "max": float(lev_s.max()),
        "pct_days_lev_gt_1": float((lev_s > 1).mean()),
        "pct_days_lev_gt_2": float((lev_s > 2).mean()),
        "pct_days_lev_gt_3": float((lev_s > 3).mean()),
        "pct_days_lev_eq_4cap": float((lev_s >= MAX_LEV - 1e-12).mean())},
    "round_trips": int(len(rtC2)),
    "short_leg_share": float((rtC2["direction"] == "short").mean()),
    "executions": int(len(rec)),
    "tradability_violations": {"buy": viol_buy, "sell": viol_sell, "price": viol_px, "seal": viol_seal,
                               "zero_activity": viol_act},
    "seal_minutes_in_sample": {"up": int((trad["涨停封板"] == 1).sum()), "down": int((trad["跌停封板"] == 1).sum())},
    "t1_counterfactual": ("无底仓纯 T+1 制度下：当日买入份额不可当日卖出，全部 "
                          f"{len(rtC2)} 趟日内往返均不可闭合（占比 100%）；空头腿无融券亦不可行。"
                          "故本策略在 A 股的可执行性完全依赖底仓 T+0 假设，"
                          "且缓冲需覆盖最高 {:.2f}x 名义本金".format(float(lev_s.max()))),
}
dump_json(constraints, "18_ashare_constraints.json")
print("BLOCK-18 ok")
print(json.dumps(constraints["lev_distribution"], ensure_ascii=False, indent=2))
''')

# ============================================================ summary
md('''## 结果速览（g30 论文主线）

- 变体 A/B/C 与 B&H 汇总指标见 `output/08_summary_stats.csv`；alpha/beta 见 `08_alpha_beta.csv`
- 全部产物清单：output/01~18 系列 + trade_record.csv + output/ext（Q12 扩展数据）
- 与论文数值的逐项对比见 `reports/comparison-report.md`（阶段 6 产出）''')

code('''# 结果速览
print("=== Summary (g30 + BH) ===")
print(SUMMARY[SUMMARY.Grid.isin(["g30", "-"])][["Variant", "Grid", "TotalReturn", "IRR", "Vol",
      "Sharpe", "HitRatio", "MDD"]].to_string(index=False))
print()
print("=== Alpha/Beta (g30) ===")
print(ALPHA_BETA[ALPHA_BETA.Grid == "g30"][["Variant", "alpha_annual", "beta", "t_alpha", "p_alpha"]]
      .to_string(index=False))
print()
print("MAIN NOTEBOOK RUN COMPLETE")
''')

# ============================================================ write notebook
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
    },
    "cells": CELLS,
}
out = ROOT / "main.ipynb"
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f"wrote {out} with {len(CELLS)} cells")
