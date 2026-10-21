# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CR-001
- stage：code_review
- from：main
- to：code_review（本会话无子代理，由 main 亲自执行该角色）
- cycle：1
- status：IN_PROGRESS

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：main.ipynb、build_nb.py、plan_code.md、data\processed\、output\、trade_record.csv
- 可写路径：work_root\review\、handoffs\08_code_review_to_main_CR-001.md
- 禁止路径：plan.md、process_log.jsonl、data\processed 冻结集、source\；审查不得修改被审代码

## 任务

- 目标：独立代码审查，严于自检，输出 review\cycle_01.md（PASS / REVISION_REQUIRED）
- 输入：main.ipynb、build_nb.py、plan_code.md、全部 output 产物、handoffs\06
- 执行要求：
  1. 未来函数逐项：σ(t,τ) rolling shift、σ_SPY,t shift、VWAP 截至 τ、信号-成交时点链、形态/RSI t−1 口径；
  2. 引擎语义：armed 新跨越再入场、反手、15:00 强平、整手、成本双边、tradability 闸门；
  3. 独立复算探针（不复用 notebook 函数，独立代码路径读 data\processed）：
     普通日、2022-01-20 案例日、2017-08-09 不完整日（240 bar）、2024-09-27 故障日的变体 A g30 成交复算；
     变体 C 份额/杠杆复算；
  4. 输出契约：plan_code.md §6 映射表全部文件存在且非空；
  5. 隔离重跑确定性：review\run_01\ 干净内核重跑，关键输出 sha256 与主线一致；
  6. 官方校验器：validate_trade_record.py 复核 + 探针（普通/15:00/封板分钟）。
- 预期输出：review\cycle_01.md、review\probe_recalc.py、review\run_01\（隔离运行）、handoffs\08 回报
- 验收标准：全部检查项有证据；发现问题分级（BLOCKER/MAJOR/MINOR）并给修复建议

## 回报

（待 code_review 角色填写）
