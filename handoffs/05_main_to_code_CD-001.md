# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-001
- stage：code_implementation
- from：main
- to：code（本会话无子代理，由 main 亲自执行该角色）
- cycle：1
- status：IN_PROGRESS

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：plan.md、plan_code.md、data\processed\（冻结产物）、data\metadata\field-dictionary.md、-mysql_data\（仅 Q12 扩展 ETF 补数）
- 可写路径：work_root\main.ipynb、work_root\requirements.txt、work_root\trade_record.csv、work_root\output\、work_root\build_notebook.py、work_root\handoffs\06_code_to_main_CD-001.md
- 禁止路径：plan.md、process_log.jsonl、data\processed\（不得改冻结产物）、source\；禁止任何外部数据源

## 任务

- 目标：按 plan_code.md BLOCK-00~18 实现 main.ipynb 并 production 从头运行成功
- 输入：plan_code.md（含 DATA_AGENT_OWNED 数据读取规则）、data\processed 冻结产物
- 执行要求：
  1. 严格遵守 DATA_AGENT_OWNED 的 bar 语义（END 标签：信号=标签 τ bar 收盘，13:00 用 11:30 bar；成交=下一分钟 bar 开盘；15:00=15:00 bar 收盘）；
  2. 变体 A/B/C × 网格 g30/g15/g05 全量回测，每网格独立资金线（¥1,000,000 起）；
  3. 全部 shift(1) 纪律：σ(t,τ)、σ_SPY,t、形态判定（t−1）、RSI（t−1）；
  4. 成本双边（万1 + ¥0.001/份/边），整手 floor(…/100)×100，权益非负检查；
  5. Q12 扩展 ETF（510500/159915/588000）分钟与日线补数经 -mysql_data 抓取，存 data\raw\ 与 output\（不动 data\processed 冻结集）；
  6. 输出契约：output\05~18 全部文件 + trade_record.csv + requirements.txt；
  7. production 模式：jupyter nbconvert 干净内核从头顺序执行，无错误、无跳过。
- 预期输出：main.ipynb、requirements.txt、trade_record.csv、output\*（05~18）、handoffs\06 回报
- 验收标准：plan_code.md §5 各 BLOCK 的"验收方法"逐条满足；nbconvert 执行成功；trade_record 官方校验器 PASS

## 回报

（待 code 角色填写）
