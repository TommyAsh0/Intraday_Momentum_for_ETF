#!/usr/bin/env python
"""CR-001 independent recalculation probes.

Deliberately re-implements the g30 variant-A engine and variant-C sizing with an
independent code path (row loops, dict lookups) reading only data/processed/*.
Compares against notebook output files. No imports from build_nb.py / main.ipynb.
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "output"
LOOKBACK = 14
VM = 1.0
COMM = 0.0001
SLIP = 0.001
SIGMA_TARGET = 0.02
MAX_LEV = 4.0
G30 = ["10:00", "10:30", "11:00", "13:00", "13:30", "14:00", "14:30"]
SIG_BAR = {"13:00": "11:30"}

results = {"probes": [], "failures": []}


def record(name, ok, detail=""):
    results["probes"].append({"name": name, "ok": bool(ok), "detail": str(detail)})
    print(("PASS" if ok else "FAIL"), name, "|", detail)
    if not ok:
        results["failures"].append(name)


# ---------- load raw frozen inputs ----------
mn = pd.read_parquet(PROC / "minute_bars_510300.parquet")
mn = mn.sort_values("trade_time").reset_index(drop=True)
daily = pd.read_csv(PROC / "daily_510300.csv", parse_dates=["trade_date"]).sort_values("trade_date")
trad = pd.read_csv(PROC / "tradability.csv", dtype={"交易日期": str, "交易时间": str})
trad["label"] = trad["交易时间"].str[:2] + ":" + trad["交易时间"].str[2:]

days = pd.DatetimeIndex(sorted(mn.trade_date.unique()))
labels = sorted(mn.hhmm.unique(), key=lambda s: int(s[:2]) * 60 + int(s[3:]))
next_label = {labels[i]: labels[i + 1] for i in range(len(labels) - 1)}

by_day = {d: g.set_index("hhmm") for d, g in mn.groupby("trade_date")}
pc_map = daily.set_index("trade_date")["pre_close"]
ret_map = daily.set_index("trade_date")["pct_chg"].div(100.0)

# tradability lookup: (date, label) -> (buyable, sellable)
tmap = {}
for r in trad.itertuples():
    d = pd.Timestamp(r.交易日期)
    tmap[(d, r.label)] = (r.可买 == 1 and r.是否有成交 == 1, r.可卖 == 1 and r.是否有成交 == 1)


def day_open(d):
    g = by_day[d]
    if "09:30" in g.index and not math.isnan(g.loc["09:30", "open"]):
        return g.loc["09:30", "open"]
    return g["open"].dropna().iloc[0]


def moves_for(d):
    g = by_day[d]
    o = day_open(d)
    return {lab: abs(g.loc[lab, "close"] / o - 1.0) for lab in g.index if lab != "09:30"}


def sigma_for(di, tau):
    sig_label = SIG_BAR.get(tau, tau)
    vals = []
    for k in range(1, LOOKBACK + 1):
        m = moves_for(days[di - k])
        if sig_label in m:
            vals.append(m[sig_label])
    if len(vals) < LOOKBACK:
        return np.nan
    return float(np.mean(vals))


def simulate_A(di, vm=VM):
    """Independent variant-A g30 simulation for one day. Returns list of
    (decision_time, exec_label, side, price)."""
    d = days[di]
    g = by_day[d]
    o = day_open(d)
    pc = pc_map.loc[d]
    base_up, base_dn = max(o, pc), min(o, pc)
    pos = 0
    armed_l = armed_s = True
    out = []
    for tau in G30:
        sig_label = SIG_BAR.get(tau, tau)
        if sig_label not in g.index:
            continue
        p = g.loc[sig_label, "close"]
        sg = sigma_for(di, tau)
        if math.isnan(sg):
            continue
        ub = base_up * (1 + vm * sg)
        lb = base_dn * (1 - vm * sg)
        if p <= ub:
            armed_l = True
        if p >= lb:
            armed_s = True
        exec_label = next_label[sig_label]
        if exec_label not in g.index:
            continue
        ep = g.loc[exec_label, "open"]
        buy_ok, sell_ok = tmap.get((d, exec_label), (True, True))
        if pos == 0:
            if p > ub and armed_l and buy_ok:
                out.append((tau, exec_label, "买入", ep))
                pos = 1
                armed_l = False
            elif p < lb and armed_s and sell_ok:
                out.append((tau, exec_label, "卖出", ep))
                pos = -1
                armed_s = False
        elif pos == 1:
            if p < lb and sell_ok:  # variant A stop = opposite band -> close + reverse
                out.append((tau, exec_label, "卖出", ep))
                pos = 0
                if p < lb and armed_s and sell_ok:
                    out.append((tau, exec_label, "卖出", ep))
                    pos = -1
                    armed_s = False
        elif pos == -1:
            if p > ub and buy_ok:
                out.append((tau, exec_label, "买入", ep))
                pos = 0
                if p > ub and armed_l and buy_ok:
                    out.append((tau, exec_label, "买入", ep))
                    pos = 1
                    armed_l = False
    if pos == 1:
        out.append(("15:00", "15:00", "卖出", g.loc["15:00", "close"]))
    elif pos == -1:
        out.append(("15:00", "15:00", "买入", g.loc["15:00", "close"]))
    return out


# ---------- probe 1: variant A g30 trades on 4 dates ----------
tr_A = pd.read_csv(OUT / "05_oppband_trades_g30.csv", parse_dates=["date"])
for d_str, note in [("2019-04-03", "ordinary"), ("2022-01-20", "case day"),
                    ("2017-08-09", "incomplete 240-bar"), ("2024-09-27", "SSE glitch zero-vol bars")]:
    d = pd.Timestamp(d_str)
    di = days.get_loc(d)
    mine = simulate_A(di)
    theirs = [(r.decision_time, r.exec_time, r.side, r.price)
              for r in tr_A[tr_A.date == d].itertuples()]
    same_seq = len(mine) == len(theirs) and all(
        m[0] == t[0] and m[1] == t[1] and m[2] == t[2] and abs(m[3] - t[3]) < 1e-9
        for m, t in zip(mine, theirs))
    record(f"A-g30 independent resim {d_str} ({note})", same_seq,
           f"mine={len(mine)} theirs={len(theirs)} "
           f"first={mine[0] if mine else None}")

# ---------- probe 2: variant C lev & shares on 3 dates ----------
tr_C = pd.read_csv(OUT / "07_dynamic_trades_g30.csv", parse_dates=["date"])
dl_C = pd.read_csv(OUT / "07_dynamic_daily_returns_g30.csv", parse_dates=["date"]).set_index("date")
rets_all = daily.set_index("trade_date")["pct_chg"].div(100.0)
for d_str in ["2018-06-11", "2021-09-01", "2025-06-24"]:
    d = pd.Timestamp(d_str)
    i = rets_all.index.get_loc(d)
    sd = float(rets_all.iloc[i - LOOKBACK:i].std(ddof=1))
    lev = min(MAX_LEV, SIGMA_TARGET / sd)
    o = day_open(days[days.get_loc(d)])
    aum0 = dl_C.loc[d, "aum_start"]
    shares = math.floor(aum0 * lev / o / 100.0) * 100
    td = tr_C[tr_C.date == d]
    ok = abs(dl_C.loc[d, "lev"] - lev) < 1e-12 and (len(td) == 0 or int(td["shares"].iloc[0]) == shares)
    record(f"C sizing {d_str}", ok, f"lev={lev:.6f} shares={shares} file_lev={dl_C.loc[d, 'lev']:.6f}")

# ---------- probe 3: sigma future-function (bands file vs independent, only past days) ----------
bands = pd.read_csv(OUT / "03_noise_bands_sample.csv", parse_dates=["date"])
for d_str, tau in [("2017-02-03", "10:00"), ("2021-03-15", "13:30"), ("2025-06-24", "14:30")]:
    d = pd.Timestamp(d_str)
    di = days.get_loc(d)
    sg = sigma_for(di, tau)
    f = bands[(bands.date == d) & (bands.tau == tau)].iloc[0]
    o = day_open(d)
    pc = pc_map.loc[d]
    ub = max(o, pc) * (1 + VM * sg)
    lb = min(o, pc) * (1 - VM * sg)
    ok = abs(f["sigma"] - sg) < 1e-12 and abs(f["UB"] - ub) < 1e-9 and abs(f["LB"] - lb) < 1e-9
    record(f"sigma/UB/LB {d_str} {tau}", ok, f"sigma={sg:.6f}")

# ---------- probe 4: vwap file internal consistency ----------
vw = pd.read_csv(OUT / "04_vwap_check.csv")
record("vwap file vwap==manual", bool((vw["vwap"] - vw["manual"]).abs().max() < 1e-9),
       f"maxdiff={(vw['vwap'] - vw['manual']).abs().max():.2e}")

# ---------- probe 5: round-trip pnl recomputation ----------
rt = pd.read_csv(OUT / "09_round_trips_C_g30.csv", parse_dates=["date"])
for tid in [int(rt["trade_id"].iloc[0]), int(rt["trade_id"].iloc[len(rt) // 2])]:
    grp = tr_C[tr_C.trade_id == tid]
    o = grp[grp.action.str.startswith("OPEN")].iloc[0]
    c = grp[grp.action.str.startswith("CLOSE")].iloc[-1]
    direction = 1 if o.action == "OPEN_LONG" else -1
    pnl = direction * (c.price - o.price) * o.shares - grp["cost"].sum()
    mine = rt[rt.trade_id == tid].iloc[0]
    record(f"round-trip pnl tid={tid}", abs(pnl - mine["pnl"]) < 1e-6,
           f"pnl={pnl:.4f} file={mine['pnl']:.4f}")

# ---------- probe 6: equity recursion & non-negativity from files ----------
for v in ["05_oppband", "06_bandvwap", "07_dynamic"]:
    for g in ["g30", "g15", "g05"]:
        dl = pd.read_csv(OUT / f"{v}_daily_returns_{g}.csv")
        rec = np.abs(dl["aum_end"] - (1_000_000.0 + (dl["ret"] * dl["aum_start"]).cumsum())).max()
        ok = rec < 1e-6 and (dl["aum_end"] > 0).all()
        record(f"equity recursion {v} {g}", ok, f"maxdiff={rec:.2e}")

# ---------- probe 7: 15:00 execution always tradable ----------
z = trad[(trad["是否有成交"] == 0) & (trad["交易时间"] == "1500")]
record("no zero-activity 15:00 bar", len(z) == 0, f"n={len(z)}")

with open(ROOT / "review" / "probe_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
n_fail = len(results["failures"])
print(f"\nPROBES DONE: {len(results['probes'])} checks, {n_fail} failed")
raise SystemExit(1 if n_fail else 0)
