# 代码审查 cycle_05（聚焦 CD-005 扩展）

- run_id：RUN-001 ｜ task_id：CR-005 ｜ 日期：2026-10-19
- 范围：DEC-014（RSI(5) 回归新增零成本口径 A/B/C）单项扩展
- 结论：**PASS**（0 BLOCKER / 0 MAJOR / 0 MINOR）

## 1. 扩展内容核对

用户裁决（2026-10-19 Q-005）：`15_rsi_regression.csv` 的因变量为变体 C 净收益（含费用）；
补做**零成本**口径下变体 A/B/C 的 RSI 回归，检验费用是否掩盖了论文 §4.5 的负相关关系。

CD-005 改动（build_nb.py → main.ipynb，42 cells）：

| 位置 | 改动 |
|---|---|
| BLOCK-15 | 追加三变体（A=opp_band、B=band_vwap、C=band_vwap+dyn_lev）零成本（commission=0、slippage=0、g30）重跑，同一 `ols_stats`/`rsi_sample.shift(1)` 口径回归；输出 `15_rsi_regression_zero_cost.csv`（3 行）与 `15_rsi_zero_cost_daily.csv`（date/rsi_lag1/ret_A/ret_B/ret_C，回归输入全留痕）；断言三变体 n 与净口径相同 |

引擎与既有 `15_rsi_regression.csv` **零改动**（哈希在 SAME 集中）。

## 2. 独立探针（review\probe_rsi_zero.py，4/4 PASS）

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | RSI(5) Wilder 独立重算（ewm α=1/5 路径重键）+ t−1 滞后对齐逐值一致（atol 1e-9）；反未来函数判别：若误用当日 RSI 则 99.0% 行不等——滞后正确 | PASS |
| 2 | 独立 OLS 实现（numpy lstsq + erfc，重新推导 se/t/p）从日收益明细 CSV 复算 A/B/C 的 beta/t_beta/p_beta/n，与产物逐值一致（<1e-9） | PASS |
| 3 | 跨 BLOCK 锚点：零成本 C 日收益复利 = 5.229076 == `16_cost_sensitivity.csv` (0,0) 行 TotalReturn（两次独立引擎调用结果一致） | PASS |
| 4 | 引擎产物不变性：对 cycle_02 基线 SAME=82、CHANGED=7（CD-003 已知图形集）、NEW=4（CD-003/004/005 各轮新增）、MISSING=无、trade_record.csv 逐字节一致、原 `15_rsi_regression.csv` 未变 | PASS |

探针过程记录：首跑 1 项 IndexingError 为探针自身布尔索引对齐笔误，修正后全过；被审代码未因此改动。

## 3. 结果数值（零成本，g30，全样本日，y 单位 bps，n=2,185）

| 变体 | α (bps) | β | t(β) | p(β) | r2 |
|---|---|---|---|---|---|
| A | −0.47 | **+0.120** | 1.63 | 0.103 | 0.0012 |
| B | +1.53 | **+0.060** | 1.05 | 0.293 | 0.0005 |
| C | +4.20 | **+0.091** | 0.83 | 0.409 | 0.0003 |
| （对照）净口径 C | — | +0.092 | 0.83 | 0.408 | 0.0003 |
| 论文锚点（SPY） | — | **−3.25** | — | **0.001** | — |

结论：剔除费用后 β 依然全部为正且不显著，与净口径几乎相同——**费用不是掩盖 RSI 效应的原因**；
T17 的 DIVERGENT 判定在零成本口径、三变体下均维持（论文的负相关机制在 510300 样本中不存在）。

## 4. 重跑与冻结输入

- 干净内核重跑 30.0s（+3 次引擎调用），EXECUTION OK
- output\ext\ 9 个冻结输入未触碰

## 结论

CD-005 扩展正确、口径与净口径完全对齐（同一 RSI、同一掩码、同一回归函数），
cycle_05 **PASS**，建议进入 AN-006 报告更新（对照报告 T17 行与 §6、复现/过程报告同步）。
