# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-005
- stage：code（扩展轮二）
- from：main
- to：code
- cycle：5
- status：IN_PROGRESS

## 任务单

用户 Q-005 裁决（2026-10-19）：`15_rsi_regression.csv` 因变量为变体 C 净收益（含费用）；补做零成本口径下变体 A/B/C 的 RSI(5) 回归。固化为 DEC-014。

实现范围（仅 BLOCK-15 追加，引擎零改动）：

1. 三变体（A=opp_band、B=band_vwap、C=band_vwap+dyn_lev）以 commission=0、slippage=0、g30 重跑，复用同一 `rsi_sample.shift(1)` 自变量与 `ols_stats` 回归函数。
2. 输出 `15_rsi_regression_zero_cost.csv`（3 行：variant/cost/alpha_bps/beta/t_beta/p_beta/n/r2/note）与 `15_rsi_zero_cost_daily.csv`（回归输入留痕：date/rsi_lag1/ret_A/ret_B/ret_C）。
3. 断言三变体 n 与净口径相同；既有 `15_rsi_regression.csv` 保持不变。
4. BLOCK-15 md 同步；build_nb.py 重建后干净内核重跑。

## 验收标准

- 干净内核 EXECUTION OK
- 不变性：除新增 2 个 CSV 外全部产物与 CD-004 后状态一致；trade_record.csv 不变；ext 未触碰
