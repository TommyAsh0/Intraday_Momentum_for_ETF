# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-004
- stage：code（扩展轮）
- from：code
- to：main
- cycle：4
- status：COMPLETE

## 回报

DEC-013 已实现并干净内核重跑通过（EXECUTION OK，42.8s；+2 次引擎调用）：

1. **BLOCK-16 追加**：三变体零滑点万 1 对照（g30，2017-01-03~2025-12-31）落盘 `output\16_cost_w1_zero_slip.csv`：
   - A（opp_band）：TR +148.8%、IRR 11.1%、Vol 10.7%、Sharpe 1.03、Hit 32.4%、MDD −9.6%、Skew +0.78、2,840 行
   - B（band_vwap）：TR +90.0%、IRR 7.7%、Vol 8.4%、Sharpe 0.92、MDD −7.6%、3,410 行
   - C（band_vwap+dyn）：TR +189.0%、IRR 13.0%、Vol 16.1%、Sharpe 0.84、MDD −21.3%、3,410 行
2. **notebook 内断言通过**：C 行与成本谱 (万1,0tick) 行 TotalReturn/Sharpe 一致（<1e-9）。
3. **不变性自检**（对 cycle_02 基线）：SAME 82 + CHANGED 7（恰为 CD-003 已知图形集）+ NEW 2（03_noise_bands_1min.csv、16_cost_w1_zero_slip.csv）；trade_record.csv 逐字节一致；ext 未触碰。

复用既有 run_backtest/perf_stats 接口，与主线 RUNS、成本谱同一函数路径，无新代码路径风险。

## 建议

main 验收后派单 CR-004 聚焦复审：口径勾稽、exec_rows 勾稽、滑点增量量级独立核验、不变性复核。
