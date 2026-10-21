# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CR-004
- stage：code_review（扩展轮）
- from：main
- to：code_review
- cycle：4
- status：IN_PROGRESS

## 任务单

对 CD-004（DEC-013 三变体零滑点万 1 对照）做聚焦复审，输出 review\cycle_04.md：

1. **独立探针 review\probe_w1z.py**（不复用 notebook 运行时状态，直读产物 CSV）：
   - 口径核验：commission=万1、slippage=0；C 行与 `16_cost_sensitivity.csv` (万1,0tick) 行一致
   - exec_rows 勾稽：与 grids\g30 成交明细行数一致（A 2,840 / B/C 3,410）
   - 滑点增量量级：移除 1 tick 滑点的期末 AUM 增量 Δ 与 Σ(每腿 shares×0.001) 同量级且略大（复利机理），比值合理区间 (0.5, 3)
   - 引擎产物不变性：对 cycle_02 基线 SAME=82 + CD-003 已知 7 变更 + 2 新增；MISSING 无；trade_record.csv 一致

## 验收标准

- cycle_04.md 结论 PASS/FAIL 明确，探针脚本留存 review\probe_w1z.py
