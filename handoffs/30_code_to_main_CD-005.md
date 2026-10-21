# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-005
- stage：code（扩展轮二）
- from：code
- to：main
- cycle：5
- status：COMPLETE

## 回报

DEC-014 已实现并干净内核重跑通过（EXECUTION OK，30.0s；+3 次引擎调用）：

1. **BLOCK-15 追加**：零成本（commission=0、slippage=0）三变体 RSI 回归，落盘 `output\15_rsi_regression_zero_cost.csv` 与回归输入留痕 `15_rsi_zero_cost_daily.csv`（2,186 行 × date/rsi_lag1/ret_A/ret_B/ret_C）。
2. **结果**（g30、全样本日、y 单位 bps、n=2,185）：
   - A：α=−0.47bps、β=+0.120、t=1.63、p=0.103、r2=0.0012
   - B：α=+1.53bps、β=+0.060、t=1.05、p=0.293、r2=0.0005
   - C：α=+4.20bps、β=+0.091、t=0.83、p=0.409、r2=0.0003
   - 对照净口径 C：β=+0.092、p=0.408——零成本与净口径几乎相同
3. **断言通过**：三变体 n=2,185 与净口径相同（同一掩码）。
4. **不变性自检**（对 cycle_02 基线）：SAME 82 + CHANGED 7（CD-003 已知集）+ NEW 4（03_1min、16_w1z、15_zc、15_zc_daily）；trade_record.csv 逐字节一致；ext 未触碰；原 15_rsi_regression.csv 未变。

解读：剔除费用后 β 依然全正且不显著，费用并非掩盖 RSI 效应的因素；T17 DIVERGENT 判定证据加强。

## 建议

main 验收后派单 CR-005 聚焦复审：RSI 独立重算与 t−1 滞后对齐、独立 OLS 复算、零成本 C 复利对成本谱 (0,0) 锚点、不变性复核。
