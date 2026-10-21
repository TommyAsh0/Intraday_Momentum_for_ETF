# CR-001 代码审查报告 — cycle_01

- run_id：RUN-001 ｜ 审查人：code_review（本会话由 main 亲自执行该角色）
- 日期：2026-10-05 ｜ 对象：main.ipynb（42 cell，build_nb.py 生成）、trade_record.csv、output\*（87 文件）
- 结论：**PASS**（0 BLOCKER / 0 MAJOR / 2 MINOR，均已在 cycle_01 内修复并复验）

## 1. 审查方法

严于自检的四路独立证据：
1. 逐行代码审读（build_nb.py 全部 cell 源码）；
2. **独立复算探针** `review/probe_recalc.py`：不复用 notebook 任何函数，以独立代码路径（逐行循环 + 字典查找）
   直读 `data/processed/*`，重算引擎交易、噪声带、仓位、整趟盈亏；
3. **隔离目录干净内核重跑** `review/run_01/`（27.4s EXECUTION OK），46 个关键输出 sha256 与主线逐一比对；
4. 官方校验器复核（validate_trade_record，3 探针）。

## 2. 未来函数逐项审计

| # | 检查项 | 实现位置 | 证据 | 结论 |
| --- | --- | --- | --- | --- |
| F1 | σ(t,τ) 噪声带只用 t−1 及以前 | BLOCK-03 `rolling(lookback).mean().shift(1)` | 探针 3：独立用 di−1..di−14 日重算 σ/UB/LB 与 `03_noise_bands_sample.csv` 差 <1e-9 | PASS |
| F2 | σ_SPY,t 只用 t−1 及以前日收益 | BLOCK-02 `rolling(14).std(ddof=1).shift(1)` | notebook 内 3 日手工复算 assert；探针 2 独立复算 lev | PASS |
| F3 | VWAP 用截至 τ 的日内累计 | BLOCK-04 `cumsum(axis=1)`，引擎取 `VWrow[sc]`（sc=信号 bar 列） | 探针 4：04 文件 vwap==manual（max diff 0） | PASS |
| F4 | 信号-成交时点链：p(τ)=标签 τ bar 收盘（13:00→11:30），成交=下一分钟 bar 开盘，15:00=收盘 bar | BLOCK-05 GRID_SPEC + 引擎 | 探针 1：4 日独立重模拟，成交序列/价格与 `05_oppband_trades_g30.csv` 完全一致 | PASS |
| F5 | 日内形态 t−1 判定 | BLOCK-12 各形态 `ser.shift(1)` | notebook 内 2 日 NR4/ID 手工验证 assert | PASS |
| F6 | RSI 自变量 t−1 | BLOCK-15 `rsi_sample.shift(1)` | 3 日 Wilder RSI 手工复算 assert | PASS |
| F7 | 带基价 max/min(Open_t, preClose_t) 时点合法 | Open_t 09:30 竞价后即知，首个决策 10:00 | 代码审读 | PASS |
| F8 | move 矩阵只用当日已实现价格 | BLOCK-03 | 探针 3 独立重算 | PASS |
| F9 | 扫描类重跑（VM/lookback/成本）沿用同一 shift 纪律 | BLOCK-14/16/17 复用 `make_sigma` 与引擎 | 代码审读 + VM=1、lookback=14 锚点 <1e-9 | PASS |

## 3. 引擎语义审计

| 项 | 结论 | 证据 |
| --- | --- | --- |
| 新跨越入场（armed 机制：回到带内/另一侧后重新武装；止损后不原地再入） | PASS | 代码审读；探针 1 独立实现同样语义后逐笔一致 |
| 反向穿越 = 平仓+反手（变体 A=反向带；B/C=同时 <LB/>UB 才反手） | PASS | 同上 |
| 15:00 强平 | PASS | 探针 7：15:00 无零成交 bar；流水含 15:00 平仓行 |
| 整手 floor(…/100)×100 | PASS | 探针 2：3 日份额复算一致；validator 多倍 100 检查 |
| 成本双边（万1×成交额 + ¥0.001×份额） | PASS | 探针 5：整趟盈亏复算 <1e-6 |
| 权益非负 + 现金递推 | PASS | 探针 6：9 条资金线递推 maxdiff ≤2.1e-8，全部为正 |
| tradability 闸门（可买/可卖/封板/零成交） | PASS | validator 3,410 笔 0 违规；2024-09-27 故障日探针一致 |

## 4. A 股规则审计

整手、免印花税、±10% 涨跌停（2019-06 前派生值已标注）、T+0 底仓假设（DEC-004，BLOCK-18 量化缓冲：
lev mean 2.20 / max 4.0 / >2x 占 55.9%）、2024-09-27 上交所故障零成交 bar 处理 —— 均合规。

## 5. 输出契约

plan_code.md §6 映射表 33 行全部有对应产物（87 个 output 文件 + trade_record.csv）。
**MINOR-1**：05/06/07 文件名与 BLOCK 文本字面顺序不一致 → 已改 plan_code.md 文本对齐实现。
**MINOR-2**：Fig2/Fig5 缺 `_data.csv` → 已补 `10_fig2_data.csv`、`10_fig5_data.csv` 并重跑（26.6s OK）。

## 6. 确定性与官方校验

- 隔离重跑确定性：**46/46 文件 sha256 一致**（`review/hashes_before.json` vs 重跑后；`review/determinism.json`）；
  MINOR 修复后第三次运行仍 46/46 一致。
- 官方 validate_trade_record：**returncode=0**（探针：20170123,1001 普通 / 20170210,1500 强平 / 20241008,0930 涨停封板分钟）。
- 独立探针：**23/23 PASS**（`review/probe_results.json`）。

## 7. 残余风险（不阻塞）

1. Q12 扩展 ETF 未建分钟级 tradability，汇总指标仅作参考（已在产物注明）。
2. 159915.SZ 分钟缺 1 日 + 8 个非标准 bar 日（Q12 参考口径）。
3. 2022-01-31 论文案例日 A 股春节休市，图形顺延至 2022-02-07 并已在图题标注。
4. 论文 T5/T6 等统计为净成本口径，A 股成本结构主导符号，阶段 6 需在报告中明确区分毛/净口径。

**Verdict: PASS — 准予进入阶段 6（结果对比分析）。**
