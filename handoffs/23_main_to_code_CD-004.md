# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-004
- stage：code（扩展轮）
- from：main
- to：code
- cycle：4
- status：IN_PROGRESS

## 任务单

用户 Q-004 裁决（2026-10-19，接受 main 建议）：将变体 A/B 补跑"万 1 + 零滑点"口径，与成本谱已有 C 行合成三变体对照表，加入对照报告成本敏感性一节。固化为 DEC-013。

实现范围（仅 BLOCK-16 追加，引擎零改动）：

1. BLOCK-16 末尾新增：A（opp_band）/B（band_vwap）/C（band_vwap+dyn_lev）三变体在 commission=0.0001、slippage=0.0、g30 下重跑，`perf_stats` 全指标 + exec_rows，落盘 `output\16_cost_w1_zero_slip.csv`。
2. notebook 内断言：C 行 TotalReturn/Sharpe 与成本谱 (万1, 0tick) 行一致（<1e-9）。
3. BLOCK-16 md 注释同步；build_nb.py 重建 main.ipynb 后干净内核重跑。

## 验收标准

- 干净内核 EXECUTION OK
- 不变性：除新增 `16_cost_w1_zero_slip.csv` 外全部产物与 CD-003 后状态一致（对 cycle_02 基线：SAME 82 + CD-003 已知 7 变更 + 2 新增）；trade_record.csv 不变；ext 冻结输入未触碰
