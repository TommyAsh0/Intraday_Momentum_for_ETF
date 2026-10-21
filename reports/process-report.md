# 流程报告：RUN-001 复现工程过程审计

- run_id：RUN-001 ｜ 论文：SSRN 4824172（Intraday Momentum, SPY）→ 510300.SH
- 运行模式：production ｜ 起止：2026-10-04 22:14 ~ 2026-10-19 00:30（含两轮修订与一轮扩展）
- 特别说明：本会话无子代理可用，analysis / data / code / code_review 四角色全部由 main 依次亲自执行；handoff 文件（01~28）记录完整交接内容，审计链不依赖子代理边界。

## 1. 阶段与门禁

| 阶段 | 任务 | 轮数 | 结果 | 关键证据 |
|------|------|------|------|----------|
| 0 初始化 | — | 1 | DONE | 工作目录唯一、原件只读归档 source\ |
| 1 论文规划 | AN-001 | 1 | COMPLETE | plan_code.md（18 代码块、T01-T33 覆盖） |
| 2 主审与范围 | Q-001 | 1 | 用户裁决固化 | DEC-001~008；用户答复 2026-10-04 |
| 3 数据验证 | DT-001 | 1 | COMPLETE | QA 21/21；mysql-request / data-bundle 双官方校验器 PASS |
| 4 代码实现 | CD-001~005 | 5 | COMPLETE | 干净内核 27~43s；94 输出 + 3,410 行流水；官方流水校验 PASS |
| 5 代码审查 | CR-001~005 | 5（cycle_01~05） | PASS | 未来函数 9 项 + 引擎 7 项 + A 股规则 5 项全 PASS；探针 23/23 + 10/10 + 5/5 + 4/4 + 4/4；隔离重跑 46/46 与 90/90；cycle_03/04/05 引擎不变性 82/90 哈希一致 |
| 6 结果分析 | AN-002~006 | 5 | COMPLETE | reports\两报告；T01-T33 逐项对照 |
| 7 最终验收 | — | 5 | PASS | validate_process_log.py：PASS（46 条事件） |

- 代码审查轮数：5（cycle_01 首轮 PASS；cycle_02/03 聚焦修订 PASS；cycle_04/05 聚焦扩展 PASS）；结果分析轮数：5（AN-002 首轮、AN-003/AN-004 修订更新、AN-005/AN-006 扩展更新）。
- 修订轮一（2026-10-05 用户 Q-002 裁决）：CD-002（VWAP 网格口径 DEC-009 / 输出 grids 分类 DEC-010 / 日内图午休轴 DEC-011）→ CR-002 cycle_02 PASS（探针 10/10、1,200 项逐值、重跑 90/90、A/B&H 不变性）→ AN-003 报告更新。
- 修订轮二（2026-10-05 用户 Q-003 裁决）：CD-003（噪声带 1 分钟全分辨率绘图 DEC-012）→ CR-003 cycle_03 PASS（探针 5/5：随机 24 点逐值、1 分钟分辨率、检查点值=引擎决策值 15,302+2,186 行；82/90 哈希不变 + 7 有意变更 + 1 新增；trade_record 不变；ext 未触碰）→ AN-004 报告更新。
- 扩展轮一（2026-10-19 用户 Q-004 裁决）：CD-004（三变体零滑点万 1 对照 DEC-013）→ CR-004 cycle_04 PASS（探针 4/4：C 行与成本谱勾稽、exec_rows 勾稽、滑点增量量级 1.33~1.56 符合复利机理、82/90 不变 + 已知 7 变更 + 2 新增）→ AN-005 报告更新。
- 扩展轮二（2026-10-19 用户 Q-005 裁决）：CD-005（RSI 回归零成本口径 A/B/C DEC-014）→ CR-005 cycle_05 PASS（探针 4/4：RSI 独立重算与滞后对齐、独立 OLS 逐值 <1e-9、复利锚点 5.229076、82/90 不变 + 已知 7 变更 + 4 新增）→ AN-006 报告更新。
- 修订中发现并修复：VWAP ×100 尺度 bug（自检发现，已加尺度断言）；BLOCK-04 变量遮蔽（s→slab）；均为运行/探针内发现并闭环，未流出到交付。cycle_03/05 探针首跑各有 1 项探针自身笔误（merge 后缀 / 布尔索引对齐），修正后全过，被审代码未改动。
- 流程日志校验：`python ../.github/harness/validators/validate_process_log.py --log process_log.jsonl` → PASS（首轮 13 条 + 修订轮一 9 条 + 修订轮二 8 条 + 扩展轮一 8 条 + 扩展轮二 8 条，共 46 条事件）。

## 2. 质量门禁汇总

| 门禁 | 结果 |
|------|------|
| 数据 QA（21 项） | 21/21 PASS |
| 官方数据校验器（mysql-request、data-bundle） | 双 PASS |
| 官方交易流水校验器（validate_trade_record + 3 探针） | PASS，3,410 条 0 违规 |
| 未来函数逐项（rolling shift、VWAP 截至 τ、信号-成交链、形态/RSI t−1 等 9 项） | 9/9 PASS |
| 独立复算探针（独立代码路径，不复用 notebook 函数） | 23/23 + 10/10 + 5/5 + 4/4 + 4/4 一致 |
| 隔离重跑确定性（干净内核，sha256） | 46/46 一致；cycle_02 90/90 一致 |
| 修订不变性（cycle_03：引擎产物哈希 vs cycle_02 基线） | 82/90 逐字节一致，7 有意变更（图+图数据），1 新增（03_noise_bands_1min.csv），trade_record.csv 不变 |
| 输出契约（plan_code.md §6 映射表文件存在且非空） | PASS |
| 论文数值锚点来源 | 全部取自 pdf_text.txt 原文，无凭记忆填写 |

## 3. 用户裁决执行核对

| 裁决 | 执行 | 证据 |
|------|------|------|
| 每 5 分钟与每 15 分钟决策 | g30 主线 + g15/g05 全量回测（A/B/C × 3 网格） | 05/06/07/09 系列 CSV 按网格分列；comparison-report T33 |
| 假设有底仓可 T+0 | EXECUTABLE_WITH_INVENTORY_T0 模式；缓冲需求量化（均值 2.20x、最大 4.00x）；T+1 反事实 100% 不可闭合 | 18_ashare_constraints.json；reproduction-report §6 |
| 全部假设写进最终报告 | 假设清单 H1-H16 | reproduction-report §2 |

## 4. 残余风险（随交付保留）

1. stk_limit 2019-06-26 前为派生值，封板标记近似（样本内封板分钟仅 8 个，影响可忽略）。
2. Table 5/6 对照的毛口径分解为成本加回估算，"A 股形态/星期结构与美股不同"为指示性结论。
3. Q12 扩展为参考口径（3 只 A 股 ETF），样本起止不一致（588000 自 2020-11）。
4. 除息日按前复权价格处理，分红现金流未计入收益（9 个除息日，单日影响 <0.5% 级）。
5. RSI 回归（§4.5）为唯一 DIVERGENT 项：可比口径下方向相反且不显著（p=0.45），已在对照报告如实标注，未做口径修饰。

## 5. 产物索引

- 计划与日志：plan.md、plan_code.md、process_log.jsonl（E0001-E0046）
- 交接：handoffs\01~34
- 代码：main.ipynb、build_nb.py、run_notebook.py、requirements.txt
- 数据：data\（raw + processed 冻结集 + metadata）
- 输出：output\（94 文件，grids 布局 + 03_noise_bands_1min.csv + 16_cost_w1_zero_slip.csv + 15_rsi_regression_zero_cost.csv + 15_rsi_zero_cost_daily.csv）、trade_record.csv
- 审查：review\cycle_01.md、cycle_02.md、cycle_03.md、cycle_04.md、cycle_05.md、probe_recalc.py、probe_vwap_grid.py、probe_noise_band_1m.py、probe_w1z.py、probe_rsi_zero.py、probe_results.json、determinism.json、run_01\、run_02\
- 报告：reports\reproduction-report.md、reports\comparison-report.md、reports\process-report.md（本文件）
