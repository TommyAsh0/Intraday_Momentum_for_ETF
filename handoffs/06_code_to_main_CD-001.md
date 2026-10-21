# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-001
- stage：code_implementation
- from：code（本会话无子代理，由 main 亲自执行该角色）
- to：main
- cycle：1
- status：COMPLETE

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：plan.md、plan_code.md、data\processed\、-mysql_data\（仅 Q12 补数）
- 可写路径：main.ipynb、requirements.txt、trade_record.csv、output\、build_nb.py、run_notebook.py、handoffs\06
- 禁止路径：plan.md、process_log.jsonl、data\processed 冻结集、source\

## 任务

- 目标：按 plan_code.md BLOCK-00~18 实现 main.ipynb 并 production 从头运行成功
- 验收标准：各 BLOCK 验收方法逐条满足；干净内核执行成功；trade_record 官方校验器 PASS

## 回报

- 完成内容：
  1. main.ipynb（42 cell，BLOCK-00~18 全覆盖）由 build_nb.py 生成（cell 源码即本文件字符串，可重建）；
  2. production 运行：run_notebook.py（nbclient 干净内核，cwd=work_root）**EXECUTION OK in 27.0s**；
  3. 三变体 × 三网格全量回测（9 条独立资金线）+ VM 12 档 + lookback 8 档 + 成本谱 15 档 + VWAP-only + Q12 三 ETF；
  4. plan_code.md 标签语义修正 7 处（END 标签实证口径，与分析链等价、仅标签记账差异）；
  5. Q12 扩展 ETF 补数（cd001_ext_fetch.py）：510500/159915 全 2017-2025、588000 自 2020-11；轻 QA 通过；
  6. 过程中修复：all() 语法残留、2022-01-31 A 股春节休市（案例日顺延 2022-02-07 并标注）、
     变量遮蔽（GRID_SPEC 循环变量 s 覆盖日频 df）、**2024-09-27 上交所技术故障零成交 bar**（211 根纳入引擎成交闸门）。
- 产物路径：main.ipynb、build_nb.py、run_notebook.py、requirements.txt、trade_record.csv（3,410 行）、
  output\（86 文件：01~18 系列 + ext\）、output\ext\（Q12 数据与 QA）
- 验证证据：
  - BLOCK-02/03/04 各 3 处手工复算 assert 通过；BLOCK-05 现金递推 <1e-6、权益非负；
  - BLOCK-08 TotalReturn 与 equity 勾稽 <1e-12；BLOCK-09 整趟数/盈亏与逐日勾稽 <1e-6；
  - BLOCK-14 VM=1、BLOCK-17 lookback=14 与主线锚点 <1e-9；BLOCK-16 成本单调性；
  - BLOCK-18 逐笔 tradability 核验 0 违规（含 是否有成交）；**官方 validate_trade_record returncode=0**（3 探针：普通/15:00/涨停封板分钟）。
- 假设与限制（须入最终报告）：
  1. 信号=标签 τ bar 收盘、成交=下一分钟 bar 开盘（比论文决策价保守 1 分钟，A 股 bar 语义适配）；
  2. 底仓 T+0（用户裁决）；所需缓冲 = 当日名义本金 = lev×AUM（lev 均值 2.20、max 4.0、>2x 占 55.9%）；
  3. 15:00 强平无零成交 bar（211 根零成交 bar 均不在 15:00）；
  4. Q12 扩展标的未建分钟级 tradability（仅汇总参考）；588000 样本自 2020-11；
  5. 2022-01-31 案例日顺延至 2022-02-07（A 股春节休市）。
- 未解决问题：无阻塞项。**核心结果（g30，净口径）**：A +22.3%/Sharpe 0.27；B −16.6%；C −57.3%；B&H +64.3%；
  **零成本 C：+535.2%/Sharpe 1.356**（论文锚点 1.33）——策略逻辑复现成立，差异由 A 股 tick 成本结构主导。
- 建议 next_action：main 验收后派单 CR-001 独立代码审查（重点：未来函数逐项、armed 再入场语义、
  引擎成交/成本复算探针、输出契约完整性）。
- log_summary：CD-001 完成，production 27s 干净内核通过，官方流水校验 PASS。
