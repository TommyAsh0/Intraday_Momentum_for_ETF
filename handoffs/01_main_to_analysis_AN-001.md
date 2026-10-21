# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：AN-001
- stage：paper_planning（PAPER_PLANNING 模式）
- from：main
- to：analysis（本会话无子代理，由 main 亲自执行该角色）
- cycle：1
- status：IN_PROGRESS

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：source\ssrn-4824172.pdf、pdf_text.txt、.github\harness\templates\
- 可写路径：work_root\plan_code.md、handoffs\02_analysis_to_main_AN-001.md
- 禁止路径：plan.md、process_log.jsonl、data\、main.ipynb、output\、review\、reports\

## 任务

- 目标：精读论文全文（正文、公式、FAQ、附录表 A1），还原推理链，枚举全部图/表/关键结论，设计逐代码块 plan_code.md。
- 输入：source\ssrn-4824172.pdf（43 页）、pdf_text.txt 提取文本、plan_code.md 模板。
- 执行要求：按论文叙述顺序设计 notebook；每个研究代码块有稳定两位序号、输入、公式、时点、输出契约与验收标准；保留 DATA_AGENT_OWNED 区块；任务清单标注可行性。
- 预期输出：plan_code.md + 本任务单背面回报（handoffs\02_analysis_to_main_AN-001.md）。
- 验收标准：论文全部图（Fig 1-10 + FAQ 图表）、表（Table 1-6、A1、FAQ 表）与关键结论一一可追踪；每块定义 NN_输出。

## 回报

（由 02_analysis_to_main_AN-001.md 承接）
