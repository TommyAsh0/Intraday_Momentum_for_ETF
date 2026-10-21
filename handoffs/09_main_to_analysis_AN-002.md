# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：AN-002
- stage：result_analysis
- from：main
- to：analysis（本会话无子代理，由 main 亲自执行该角色）
- cycle：1
- status：IN_PROGRESS

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：pdf_text.txt、plan_code.md、output\、trade_record.csv、review\、handoffs\01-08
- 可写路径：work_root\reports\、handoffs\10_analysis_to_main_AN-002.md
- 禁止路径：plan.md、process_log.jsonl、data\processed 冻结集、source\；分析不得修改代码与产物（发现产物问题时回到 main 派单 code 修复）

## 任务

- 目标：论文逐图逐表对比分析，输出两份报告
- 输入：pdf_text.txt（论文全文抽取）、output\ 全部产物（87 文件 + trade_record.csv）、review\cycle_01.md 审查结论
- 执行要求：
  1. 论文锚点补全：从 pdf_text.txt 提取 T1/T2（变体 A/B 完整行）、T4（Trades/Hit Rate/Avg PnL×Share）、T5（NR4 行：+22bps t=5.14）、T6（周三行：+18bps t=3.42）、§4.5（RSI β=−3.25 p=0.001）、Fig9（VM 最优≈1.5）、Q22（VWAP-only 表）、A1（偏度/最差日）——禁止凭记忆填论文数值；
  2. reports\reproduction-report.md：复现方法、假设清单（用户裁决全部写明：5/15 分钟双网格、底仓 T+0、信号=bar 收盘/成交=次 bar 开盘时点口径、成本 0.1 元+1tick、VIX 代理、案例日春节顺延、Q12 参考口径）、数据链路、验证证据（QA 21/21、审查 PASS、探针 23/23、重跑 46/46）、核心结果；
  3. reports\comparison-report.md：逐图逐表对照表（T01-T33 每行：论文值 vs 复现值 vs 判定 REPRODUCED / APPROXIMATE / NOT_COMPARABLE / NOT_ATTEMPTED + 原因），主结论分逻辑层与数值层，成本机制量化解释（tick 成本 2.5bps vs SPY penny 0.25bps）；
  4. 判定标准：逻辑/结构层面符号与单调性一致 → REPRODUCED；方向一致量级不同且可解释 → APPROXIMATE；市场/样本/成本结构差异 → NOT_COMPARABLE；未实施 → NOT_ATTEMPTED。
- 预期输出：reports\reproduction-report.md、reports\comparison-report.md、handoffs\10 回报
- 验收标准：每个论文图表均有对照行；论文数值全部来自 pdf_text.txt 原文；假设清单完整；报告引用产物用绝对路径

## 回报

（待 analysis 角色填写）
