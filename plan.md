# 论文复现流程控制计划

> 本文件是唯一流程状态源，只允许 main 修改。其他文件中的任务状态仅作证据，不覆盖本文件。
> 本次运行说明：本会话无子代理可用，analysis / data / code / code_review 各角色全部由 main 依次亲自执行；handoff 文件记录各角色交接的完整内容，保证审计链完整。

## 1. 运行状态

<!-- HARNESS_STATE_START -->
```yaml
schema_version: 1
run_id: "RUN-001"
work_root: "D:\\quantitative_project\\复现工程\\Intraday_Momentum_for_ETF"
source_paper: "source\\ssrn-4824172.pdf"
overall_status: DONE
current_stage: done
current_owner: main
last_completed_step: final_acceptance (round 5)
next_action: none (extension round 2 complete; user report delivered)
review_cycle: 5
analysis_cycle: 5
run_mode: production
data_scope_decision: DONE
market_mode: EXECUTABLE_WITH_INVENTORY_T0
data_status: READY
code_review_status: PASS (cycle_01 ~ cycle_05)
result_analysis_status: DONE (AN-002 ~ AN-006)
updated_at: "2026-10-19T17:05:00+08:00"
```
<!-- HARNESS_STATE_END -->

## 2. 用户目标与附加指令

- 原始目标：以 `.github\agents\main.agent.md` 总控身份，按 harness 工程复现论文 `Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)`（Zarattini, Aziz, Barbon；SSRN 4824172；2025-09-22 版）。
- 目标市场：按 harness 定位（大 A 论文复现）迁移至中国 A 股 ETF；论文市场为美股 SPY。
- 特别要求：严格遵循阶段门禁与全部交付契约；原论文只读；不允许静默缩样/换源/降频。
- 明确排除项：无。

## 3. 固化范围与决策

| 决策 ID | 项目 | 决定 | 依据 | 是否需用户确认 | 状态 |
|---|---|---|---|---|---|
| DEC-001 | 标的 | 510300.SH（沪深300ETF华泰柏瑞，A 股最像 SPY 的大盘宽基 ETF）；基准回归用 510300 自身日收益（论文即 SPY 自身），000300.SH 作对照 | 论文单标的 + harness A 股定位 | approved_from_user_request（2026-10-04 无异议） | DONE |
| DEC-002 | 样本与日期 | 2017-01-01 ~ 2025-12-31（etf_min 实际覆盖上限，约 9 年）；日频数据自 2016-11 起（14 日波动预热） | main 冒烟验证（2026-10-04）：etf_min 510300.SH 2017-01-03 起有数据、2025-12-31 止 | approved_from_user_request（2026-10-04 无异议） | DONE |
| DEC-003 | 频率与交易时点 | 1 分钟 bar（**结束时间标签**，DT-001 实证：09:30 为开盘集合竞价 bar，09:31..11:30 与 13:01..15:00 为 1 分钟 bar，241 bar/日，无 13:00 标签）；决策网格三档：30 分钟档 {10:00,10:30,11:00,13:00,13:30,14:00,14:30}（论文忠于口径主线）、15 分钟档 {10:00,10:15,…,14:45}、5 分钟档 {10:00,10:05,…,14:55}（用户 2026-10-04 要求新增）；信号价 = 时点 τ 标签 bar 收盘（13:00 用 11:30 bar），成交价 = 下一分钟 bar 开盘（13:00 时为 13:01 bar）；收盘 15:00 bar 收盘强制平仓 | 论文半点规则 + 用户 5/15 分钟变体 + A 股午休适配 + DT-001 bar 语义实证 | approved_from_user_request（2026-10-04） | DONE |
| DEC-004 | 市场规则模式 | 假设已有底仓可 T+0（用户 2026-10-04 答复）：先卖后买/先买后卖日内均可合法闭合；前提为底仓+现金缓冲 ≥ 当日交易名义本金，动态仓位高杠杆日的缓冲需求由 BLOCK-18 量化并在最终报告写明；涨跌停/停牌仍以 tradability 逐笔核验 | approved_from_user_request + A 股制度事实 | approved_from_user_request | DONE |
| DEC-005 | 成本模型 | ETF 免印花税；基准佣金 万1（0.01%/边，无最低 5 元）+ 滑点 1 个最小价位（¥0.001/份/边）；另做佣金×滑点敏感性谱（对应论文 §4.6/Figure 10） | A 股 ETF 费率事实 + 论文成本结构 | approved_from_user_request（2026-10-04 无异议） | DONE |
| DEC-006 | VIX 缺失替代 | 无 VIX 数据源；Figure 8 波动机制用 14 日已实现波动 σ_SPY,t（策略本身即计算）作为开盘可得代理 | 数据可行性 | approved_from_user_request（2026-10-04 无异议） | DONE |
| DEC-007 | 起始资金 | ¥1,000,000（对应论文 $100,000，整手取整后跟踪误差小） | 论文口径映射 | 否 | DONE |
| DEC-008 | 整手规则 | ETF 100 份一手，份额向下取整至 100 的整数倍 | A 股规则 | 否 | DONE |
| DEC-009 | VWAP 口径修订 | VWAP 按**决策间隔 bar** 聚合计算（用户 2026-10-05 裁决）：网格 bar =（前一信号标签， 当前信号标签] 的 1 分钟 bar 合计，VWAP_g(τ)=Σ(close_bar×vol_bar)/Σvol_bar 日内累计；13:00 用 11:30 bar；午休无 bar 自然跳过；零成交 bar 不产生增量。替代首轮的 1 分钟 amount/vol 口径 | 用户 2026-10-05 修订要求③："block-04 的 vwap 应根据检查时间间隔算出" | approved_from_user_request | DONE |
| DEC-010 | 输出布局修订 | output\ 按参数分类：网格相关产物入 `output\grids\g30|g15|g05\`（04_vwap_check、05/06/07 trades/daily/equity、09_round_trips）；网格无关与全网格汇总（01/02/03、08、09_trade_level_stats、10 图、11~18）留根目录；`output\ext\` 为 DT-001 冻结输入，保留不动；BLOCK-00 运行时清理 output 下旧产物（保留 ext） | 用户 2026-10-05 修订要求①："输出按不同参数分类整理" | approved_from_user_request | DONE |
| DEC-011 | 日内图表午休处理 | 日内图（Fig1/2/4/5 及数据 CSV）横轴改为**交易分钟序号**（0..239），午休（11:30/13:01）以竖虚线标注、不占轴长，刻度显示真实时刻；消除午休断档造成的虚假斜线与留白 | 用户 2026-10-05 修订要求② | approved_from_user_request | DONE |
| DEC-012 | 噪声带 1 分钟分辨率绘图 | σ/UB/LB 自首轮起即在 240 个 1 分钟价格标签上计算（τ 为 1 分钟离散时点，论文 §3 口径）；日内图 UB/LB 改按 1 分钟全分辨率绘制（删除 g30 检查点抽样 step 连线）；新增 `03_noise_bands_1min.csv`（全部日 × 240 时点）；图 1/2/4 数据 CSV 附 sigma/UB/LB 列；交易决策仍只在网格时点发生，引擎与全部数值结果不变 | 用户 2026-10-05 修订："τ 是 1 分钟的离散时间点，而论文也是这样" | approved_from_user_request | DONE |
| DEC-013 | 三变体零滑点万 1 对照 | 成本敏感性新增 A/B/C 在 commission=万1、slippage=0、g30 下的完整指标对照（`16_cost_w1_zero_slip.csv`，BLOCK-16 追加，复用 run_backtest/perf_stats 同一路径）；C 行与成本谱 (万1,0tick) 行断言勾稽；纯新增分析口径，既有数值与判定不变 | 用户 2026-10-19："把三种变体在零滑点万 1 口径的对照表加进成本敏感性一节" | approved_from_user_request | DONE |
| DEC-014 | RSI 回归零成本口径 | §4.5 RSI(5) 回归新增零成本（commission=0、slippage=0）A/B/C 三变体（`15_rsi_regression_zero_cost.csv` + 回归输入留痕 `15_rsi_zero_cost_daily.csv`，BLOCK-15 追加，同一 RSI(t−1) 自变量与 ols_stats 口径）；结论：β 全正不显著，费用非掩盖因素，T17 DIVERGENT 维持；既有净口径 CSV 不变 | 用户 2026-10-19："如果不带费用的情况下，回归变体A,B,C的回归是多少？" | approved_from_user_request | DONE |

## 4. 阶段门禁

| 阶段 | 负责人 | 必要输入 | 预期产物 | 通过标准 | 状态 | 证据 |
|---|---|---|---|---|---|---|
| 0 初始化 | main | 用户请求、论文 | 工作目录、计划、日志 | 路径唯一且原件只读 | DONE | 目录已建，PDF 已归档 source\，pdf_text.txt 为提取文本 |
| 1 论文规划 | analysis | 论文、附加指令 | plan_code.md | 图表与代码块覆盖完整 | DONE | plan_code.md：18 代码块、32 任务全覆盖论文 10 图 7 表与 FAQ；handoffs\02 |
| 2 主审与范围 | main | plan_code.md | 固化决策 | 无关键歧义 | DONE | DEC-001~008 固化；Q-001 用户裁决（5/15 分钟网格 + 底仓 T+0） |
| 3 数据验证 | data | 数据任务单 | 数据链路、manifest、质量报告 | MySQL 数据完整且对齐 | DONE | QA 21/21 PASS；validate_mysql_request 与 validate_data_bundle 双 PASS；handoffs\04 |
| 4 代码实现 | code | 已批准计划和数据 | notebook、依赖、流水、输出 | production 运行完成 | DONE | CD-005 完成：干净内核 30.0s；SAME 82 + 已知 7 变更 + 4 新增；trade_record 不变；handoffs\30 |
| 5 代码审查 | code_review | 全部实现和证据 | review\cycle_NN.md | PASS | DONE | cycle_05 PASS（0B/0M/0MINOR）：零成本 RSI 回归探针 4/4（RSI 独立重算与滞后对齐、独立 OLS <1e-9、复利锚点 5.229076、不变性）；handoffs\32 |
| 6 结果分析 | analysis | 审查通过结果 | reports\两报告 | 逐项比较完成 | DONE | AN-006：三报告 + plan_code.md 按 cycle_05 更新（T17 全口径），既有数值与判定维持；handoffs\34 |
| 7 最终验收 | main | 全部产物 | 用户汇报 | 所有门禁闭合 | DONE | 扩展轮二 validate_process_log PASS（46 事件）；§9 验收 7/7 PASS（修订版） |

## 5. 工作任务表

| 任务 ID | 阶段 | 负责人 | 依赖 | 输入 | 预期输出 | 验收标准 | 状态 | 最后证据 |
|---|---|---|---|---|---|---|---|---|
| AN-001 | 论文规划 | analysis | 初始化 | source\ssrn-4824172.pdf | plan_code.md | 图表全覆盖、代码块可追踪 | DONE | handoffs\02_analysis_to_main_AN-001.md |
| DT-001 | 数据验证 | data | AN-001+用户裁决 | 数据任务单 | manifest、字段字典、质量报告、冻结快照 | MySQL 完整对齐 | DONE | handoffs\04；QA 21/21 PASS；双官方校验器 PASS |
| CD-001 | 代码实现 | code | DT-001 | plan_code.md + 数据 | main.ipynb、requirements.txt、trade_record.csv、output\* | production 从头运行成功 | DONE | handoffs\06；EXECUTION OK 27s；流水校验 PASS |
| CR-001 | 代码审查 | code_review | CD-001 | 全部实现 | review\cycle_01.md | PASS | DONE | cycle_01 PASS；handoffs\08 |
| AN-002 | 结果分析 | analysis | CR-001 | 审查通过结果 | reports\两报告 | 逐图表比较完成 | DONE | handoffs\10；reports\reproduction-report.md、comparison-report.md |
| CD-002 | 代码修订 | code | Q-002 用户裁决 | DEC-009/010/011 | 修订后 main.ipynb、新布局 output\ | production 重跑通过 + 流水校验 | DONE | handoffs\12；27.1s 通过；流水 PASS；A/B&H 不变 |
| CR-002 | 修订复审 | code_review | CD-002 | 修订后全部实现 | review\cycle_02.md | PASS | DONE | cycle_02 PASS；探针 10/10；重跑 90/90；handoffs\14 |
| AN-003 | 报告更新 | analysis | CR-002 | 修订后结果 | reports\三报告更新 | 数值与新结果一致 | DONE | handoffs\16；数值与产物逐项核对一致 |
| CD-003 | 代码修订二 | code | Q-003 用户裁决 | DEC-012 | 1 分钟全分辨率噪声带图 + 03_noise_bands_1min.csv | production 重跑通过 + 引擎产物不变性 | DONE | handoffs\18；28.7s 通过；82/90 一致 + 7 变更 + 1 新增 |
| CR-003 | 修订复审二 | code_review | CD-003 | 修订后全部实现 | review\cycle_03.md | PASS | DONE | cycle_03 PASS；探针 5/5；handoffs\20 |
| AN-004 | 报告更新二 | analysis | CR-003 | 修订后状态 | reports\三报告 + plan_code.md 更新 | 表述与产物一致，数值与判定维持 | DONE | handoffs\22 |
| CD-004 | 代码扩展 | code | Q-004 用户裁决 | DEC-013 | 三变体零滑点万 1 对照（16_cost_w1_zero_slip.csv） | production 重跑通过 + 引擎产物不变性 | DONE | handoffs\24；42.8s 通过；SAME 82 + 已知 7 变更 + 2 新增 |
| CR-004 | 扩展复审 | code_review | CD-004 | 扩展后全部实现 | review\cycle_04.md | PASS | DONE | cycle_04 PASS；探针 4/4；handoffs\26 |
| AN-005 | 报告更新三 | analysis | CR-004 | 扩展后状态 | reports\三报告 + plan_code.md 更新 | 对照表数值与产物一致，既有数值与判定维持 | DONE | handoffs\28 |
| CD-005 | 代码扩展二 | code | Q-005 用户裁决 | DEC-014 | 零成本 RSI 回归 A/B/C（15_rsi_regression_zero_cost.csv 等） | production 重跑通过 + 引擎产物不变性 | DONE | handoffs\30；30.0s 通过；SAME 82 + 已知 7 变更 + 4 新增 |
| CR-005 | 扩展复审二 | code_review | CD-005 | 扩展后全部实现 | review\cycle_05.md | PASS | DONE | cycle_05 PASS；探针 4/4；handoffs\32 |
| AN-006 | 报告更新四 | analysis | CR-005 | 扩展后状态 | reports\三报告 + plan_code.md 更新 | 回归数值与产物一致，既有数值与判定维持 | DONE | handoffs\34 |

## 6. 阻塞项与用户裁决

| 问题 ID | 提出方 | 问题 | 可选方案及影响 | 是否已询问用户 | 用户决定 | 状态 |
|---|---|---|---|---|---|---|
| Q-001 | main | DEC-001~006 汇总：标的 510300.SH、样本 2017-01~2025-12、决策时点、可执行性标记、成本模型（万1+1tick）、VIX→已实现波动代理 | 见 DEC 各行 | 是（2026-10-04） | 用户答复：决策时点改为"每5分钟和每15分钟决策"（保留30分钟档为论文主线并新增两档变体）；可执行性改为"假设有底仓可T+0"；其余无异议，全部假设须在最终报告写明 | DONE |
| Q-003 | main | 日内图 UB/LB 为半小时步进线：噪声带按检查点间隔还是按 1 分钟绘制？ | ① 维持检查点步进（与决策网格一致但不符合论文 §3 的 τ=1 分钟口径）；② 按 1 分钟全分辨率绘制（σ 矩阵本为 1 分钟口径，仅改图形与输出分辨率，引擎不变） | 是（2026-10-05） | 用户裁决：τ 是 1 分钟的离散时间点，论文也是这样 → 方案②，固化 DEC-012 | DONE |
| Q-004 | main | 费率调整为万 1 的结果？（万 1 本即基准佣金口径；关键在滑点假设） | ① 仅答复既有成本谱数值；② 补跑 A/B 零滑点万 1 口径，三变体对照表加入成本敏感性一节（纯新增，不改既有结果） | 是（2026-10-19） | 用户裁决：采用方案② → 固化 DEC-013 | DONE |
| Q-005 | main | 15_rsi_regression.csv 因变量为含费用净收益：不带费用时 A/B/C 的回归是多少？ | 零成本（commission=0、slippage=0）重跑三变体并回归，输出新 CSV（纯新增，净口径 CSV 不变） | 是（2026-10-19） | 用户裁决：直接执行 → 固化 DEC-014 | DONE |

## 7. 交接登记

| 时间 | from | to | 任务 ID | 任务单/回报 | 结果 | 日志事件 |
|---|---|---|---|---|---|---|
| 2026-10-04 22:25 | main | analysis | AN-001 | handoffs\01_main_to_analysis_AN-001.md | 派单 | E0002 |
| 2026-10-04 22:40 | analysis | main | AN-001 | handoffs\02_analysis_to_main_AN-001.md | COMPLETE | E0003 |
| 2026-10-04 22:49 | user | main | Q-001 | 用户答复 | 决策固化 | E0005 |
| 2026-10-04 23:04 | main | data | DT-001 | handoffs\03_main_to_data_DT-001.md | 派单 | E0006 |
| 2026-10-04 23:34 | data | main | DT-001 | handoffs\04_data_to_main_DT-001.md | COMPLETE | E0007 |
| 2026-10-05 12:15 | main | code | CD-001 | handoffs\05_main_to_code_CD-001.md | 派单 | E0008 |
| 2026-10-05 13:05 | code | main | CD-001 | handoffs\06_code_to_main_CD-001.md | COMPLETE | E0009 |
| 2026-10-05 13:10 | main | code_review | CR-001 | handoffs\07_main_to_code_review_CR-001.md | 派单 | E0010 |
| 2026-10-05 13:40 | code_review | main | CR-001 | handoffs\08_code_review_to_main_CR-001.md | COMPLETE(PASS) | E0011 |
| 2026-10-05 14:00 | main | analysis | AN-002 | handoffs\09_main_to_analysis_AN-002.md | 派单 | E0012 |
| 2026-10-05 15:10 | analysis | main | AN-002 | handoffs\10_analysis_to_main_AN-002.md | COMPLETE | E0013 |
| 2026-10-05 17:05 | user | main | Q-002 | 用户修订裁决（3 项） | 决策固化 | E0015 |
| 2026-10-05 17:15 | main | code | CD-002 | handoffs\11_main_to_code_CD-002.md | 派单 | E0016 |
| 2026-10-05 18:00 | code | main | CD-002 | handoffs\12_code_to_main_CD-002.md | COMPLETE | E0017 |
| 2026-10-05 18:10 | main | code_review | CR-002 | handoffs\13_main_to_code_review_CR-002.md | 派单 | E0018 |
| 2026-10-05 18:40 | code_review | main | CR-002 | handoffs\14_code_review_to_main_CR-002.md | COMPLETE(PASS) | E0019 |
| 2026-10-05 19:00 | main | analysis | AN-003 | handoffs\15_main_to_analysis_AN-003.md | 派单 | E0020 |
| 2026-10-05 19:20 | analysis | main | AN-003 | handoffs\16_analysis_to_main_AN-003.md | COMPLETE | E0021 |
| 2026-10-05 21:05 | user | main | Q-003 | 用户修订裁决（噪声带 1 分钟分辨率） | 决策固化 DEC-012 | E0023 |
| 2026-10-05 21:10 | main | code | CD-003 | handoffs\17_main_to_code_CD-003.md | 派单 | E0024 |
| 2026-10-05 21:20 | code | main | CD-003 | handoffs\18_code_to_main_CD-003.md | COMPLETE | E0025 |
| 2026-10-05 21:22 | main | code_review | CR-003 | handoffs\19_main_to_code_review_CR-003.md | 派单 | E0026 |
| 2026-10-05 21:30 | code_review | main | CR-003 | handoffs\20_code_review_to_main_CR-003.md | COMPLETE(PASS) | E0027 |
| 2026-10-05 21:32 | main | analysis | AN-004 | handoffs\21_main_to_analysis_AN-004.md | 派单 | E0028 |
| 2026-10-05 21:38 | analysis | main | AN-004 | handoffs\22_analysis_to_main_AN-004.md | COMPLETE | E0029 |
| 2026-10-19 00:12 | user | main | Q-004 | 用户扩展裁决（零滑点万 1 对照表入成本节） | 决策固化 DEC-013 | E0031 |
| 2026-10-19 00:15 | main | code | CD-004 | handoffs\23_main_to_code_CD-004.md | 派单 | E0032 |
| 2026-10-19 00:20 | code | main | CD-004 | handoffs\24_code_to_main_CD-004.md | COMPLETE | E0033 |
| 2026-10-19 00:21 | main | code_review | CR-004 | handoffs\25_main_to_code_review_CR-004.md | 派单 | E0034 |
| 2026-10-19 00:25 | code_review | main | CR-004 | handoffs\26_code_review_to_main_CR-004.md | COMPLETE(PASS) | E0035 |
| 2026-10-19 00:26 | main | analysis | AN-005 | handoffs\27_main_to_analysis_AN-005.md | 派单 | E0036 |
| 2026-10-19 00:29 | analysis | main | AN-005 | handoffs\28_analysis_to_main_AN-005.md | COMPLETE | E0037 |
| 2026-10-19 16:45 | user | main | Q-005 | 用户扩展裁决（RSI 回归零成本口径 A/B/C） | 决策固化 DEC-014 | E0039 |
| 2026-10-19 16:48 | main | code | CD-005 | handoffs\29_main_to_code_CD-005.md | 派单 | E0040 |
| 2026-10-19 16:53 | code | main | CD-005 | handoffs\30_code_to_main_CD-005.md | COMPLETE | E0041 |
| 2026-10-19 16:55 | main | code_review | CR-005 | handoffs\31_main_to_code_review_CR-005.md | 派单 | E0042 |
| 2026-10-19 16:59 | code_review | main | CR-005 | handoffs\32_code_review_to_main_CR-005.md | COMPLETE(PASS) | E0043 |
| 2026-10-19 17:00 | main | analysis | AN-006 | handoffs\33_main_to_analysis_AN-006.md | 派单 | E0044 |
| 2026-10-19 17:04 | analysis | main | AN-006 | handoffs\34_analysis_to_main_AN-006.md | COMPLETE | E0045 |

## 8. 断点恢复检查点

- 运行已完结（含两轮修订与两轮扩展）：overall_status DONE（2026-10-19 17:05）；首轮 E0001-E0014，修订轮一 E0015-E0022，修订轮二 E0023-E0030，扩展轮一 E0031-E0038，扩展轮二 E0039-E0046；全部门禁闭合，§9 验收 7/7 PASS
- 最终产物：reports\reproduction-report.md、comparison-report.md、process-report.md（均为 AN-006 扩展后版本）
- 恢复前必须核验的文件：plan.md、process_log.jsonl、reports\三报告、review\cycle_05.md
- 不得重复的昂贵操作：MySQL 抓取（raw 幂等）；output\ext\ 为 DT-001 冻结输入；notebook 重跑 ~30s 可重复
- 最近日志事件 ID：E0046

## 9. 最终验收

| 验收项 | 结果 | 证据/路径 | 残余风险 |
|---|---|---|---|
| 论文项目覆盖 | PASS | plan_code.md §6 映射 T01-T33；comparison-report §3：主体 10 图 7 表全覆盖 + FAQ 11 项；NOT_ATTEMPTED 4 项均有原因（T19 实盘实验/T25 期货数据/T26 参数不可移植/T29 VIX 缺失） | 无 |
| 数据完整与时间对齐 | PASS | data\metadata\dt001_qa_report.json（21/21）；mysql-request-result.json；data-bundle-result.json；handoffs\04 | 派生涨跌停段（2017-2019H1）封板标记为近似，影响可忽略 |
| notebook 可重跑 | PASS | run_notebook.py 干净内核 27s（修订/扩展后 26.8~42.8s 四次）；cycle_02 review\run_02\determinism_02.json 重跑 90/90 sha256 一致；cycle_03/04 重跑 SAME 82 + 已知变更 + 新增逐项核验 | 无 |
| 输出映射完整 | PASS | cycle_02 输出契约：plan_code.md §6（含 grids 新布局）全部文件存在且非空（90 文件 + trade_record.csv）；cycle_03/04/05 新增 03_noise_bands_1min.csv、16_cost_w1_zero_slip.csv、15_rsi_regression_zero_cost.csv、15_rsi_zero_cost_daily.csv（94 文件）；ext 冻结输入 9 文件未被各轮修订触碰 | 无 |
| 未来函数检查 | PASS | cycle_01 未来函数 9 项全 PASS + 探针 23/23；cycle_02 网格 VWAP 未来函数边界 69/69 有判别力样本全变、13:00=11:30 语义、零成交零增量、止损 5/5（probe_vwap_grid.py 10/10） | 无 |
| A 股规则检查 | PASS | validate_trade_record PASS（3,410 条 + 3 探针，修订后复核）；18_ashare_constraints.json 五类违规全 0；整手/涨跌停/停牌/封板/零成交闸门 | 无底仓时策略 100% 不可执行（T+1 反事实已量化并写入报告） |
| 结果差异解释 | PASS | comparison-report §4 成本机制量化：毛 edge 同量级（≈4-5bps/趟）、成本结构差 ≈25 倍（往返 7.7bps vs 0.3bps）；零成本锚点 Sharpe 1.395≈论文 1.33（+4.9%） | T14/T15 毛口径分解为成本加回估算（指示性）；RSI 回归 DIVERGENT 一项已如实标注 |
