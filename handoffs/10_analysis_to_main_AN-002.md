# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：AN-002
- stage：result_analysis
- from：analysis
- to：main
- cycle：1
- status：COMPLETE

## 回报

- 论文锚点全部从 pdf_text.txt 原文提取并核对：T1/T2/T3/A1（变体行+偏度/最差/最好日）、T4（三变体交易级）、T5（NR4 +22bps t=5.14 等 9 行）、T6（周三 +18bps t=3.42 等 5 行）、§4.5（β=−3.25 p=0.001）、Fig8（VIX>6≈1.50、VIX>40→3.50、极高回落）、Fig9（VM≈1.5 最优、VM=1 为论文采用值）、Q6（5~90 日八行，90 最优 1.50）、Q7（10/10 正）、Q12（组合 Sharpe>2）、Q13（期货 33 品种、2 负、均值 0.60、组合 1.65）、Q22（7,964→6,728、Sharpe 1.35→1.17）、Q23（$0.09/股、SPY $68→$608）。
- 产出 reports\reproduction-report.md：假设清单 H1-H12（含用户裁决全部写明：5/15 分钟双网格、底仓 T+0、信号/成交时点、成本、VIX 代理、案例日顺延、Q12 参考口径）、数据链路、验证证据（QA 21/21、审查 PASS、探针 23/23、重跑 46/46、流水 3,410 条 0 违规）、核心结果。
- 产出 reports\comparison-report.md：T01-T33 逐图逐表对照（每项：论文值 vs 复现值 vs 判定+原因）。判定汇总：REPRODUCED 11、APPROXIMATE 9、DIVERGENT 1（T17 RSI 回归，方向相反 p=0.45）、NOT_COMPARABLE 7、NOT_ATTEMPTED 4（均有原因）。
- 主结论：逻辑层 REPRODUCED（零成本 Sharpe 1.356≈论文 1.33；Fig8/Q6/Q19/Q7/多空腿/VWAP-only 交易数结构一致）；数值层 NOT_COMPARABLE（市场/样本 9y vs 17y/成本结构三重差异）；成本机制量化：毛 edge 两边同量级（≈4-5bps/趟），成本结构差 ≈25 倍（往返 7.7bps vs 0.3bps），为净收益相反的全部根源；VM≥1.8 净口径转正（VM=2.0：+48.1%/Sharpe 0.45）。
- 发现产物无需返工的问题：无 BLOCKER/MAJOR；残余风险 4 项已写入对照报告 §6（派生涨跌停段、T14/T15 毛口径为估算、Q12 参考口径、除息日分红未计）。
- 建议：main 验收后进入阶段 7 最终验收（process log 校验 + process-report + plan.md §9 收尾）。
