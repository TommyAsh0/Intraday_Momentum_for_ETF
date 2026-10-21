# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：AN-006
- stage：result_analysis（扩展轮二）
- from：main
- to：analysis
- cycle：5
- status：IN_PROGRESS

## 任务单

以 CR-005 cycle_05 PASS 后状态更新报告（本轮为纯新增分析口径，既有数值与判定全部维持）：

1. **comparison-report.md**：T17 行复现值更新为"净口径 C + 零成本 A/B/C"全口径（β 全正不显著，费用非掩盖因素，DIVERGENT 维持）；头部 task_id 加 AN-006、产物版本改 cycle_05；§6 修订记录补扩展轮二段。
2. **reproduction-report.md**：§4 验证表加 cycle_05 行；§7 产物清单 94 文件；§8 修订记录补扩展轮二。
3. **process-report.md**：阶段表 CD/CR/AN 轮数改 5；补扩展轮二流程行；日志口径 46 条；§2 探针计数 +4/4；§5 产物索引更新。
4. **plan_code.md §6**：BLOCK-15 行补 `15_rsi_regression_zero_cost.csv`、`15_rsi_zero_cost_daily.csv`（DEC-014）。

## 验收标准

- 回归数值与 `output\15_rsi_regression_zero_cost.csv` 逐项一致；不改动任何既有数值与判定
