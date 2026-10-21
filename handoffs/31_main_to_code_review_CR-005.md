# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CR-005
- stage：code_review（扩展轮二）
- from：main
- to：code_review
- cycle：5
- status：IN_PROGRESS

## 任务单

对 CD-005（DEC-014 零成本 RSI 回归 A/B/C）做聚焦复审，输出 review\cycle_05.md：

1. **独立探针 review\probe_rsi_zero.py**（直读产物 CSV + data\processed 日线，不复用 notebook 运行时）：
   - RSI(5) Wilder 独立重算（ewm α=1/5）与 `15_rsi_zero_cost_daily.csv` 的 rsi_lag1 列逐值核对，验证 t−1 滞后对齐（反未来函数：若误用当日 RSI 应有高比例不等）
   - 独立 OLS 实现（numpy lstsq + erfc，重新推导 se/t/p）从日收益明细复算 A/B/C 的 beta/t/p/n 并逐值核对
   - 跨 BLOCK 锚点：零成本 C 日收益复利 == `16_cost_sensitivity.csv` (0,0) 行 TotalReturn
   - 引擎产物不变性：对 cycle_02 基线 SAME=82 + 已知 7 变更 + 4 新增；MISSING 无；trade_record.csv 一致；原 15_rsi_regression.csv 未变

## 验收标准

- cycle_05.md 结论 PASS/FAIL 明确，探针脚本留存 review\probe_rsi_zero.py
