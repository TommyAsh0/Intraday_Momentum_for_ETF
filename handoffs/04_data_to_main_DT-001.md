# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：DT-001
- stage：data_validation
- from：data（本会话无子代理，由 main 亲自执行该角色）
- to：main
- cycle：1
- status：COMPLETE

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：plan.md、plan_code.md、-mysql_data\
- 可写路径：work_root\data\、plan_code.md 的 DATA_AGENT_OWNED 区块、本文件
- 禁止路径：plan.md、process_log.jsonl、main.ipynb、output\、review\、reports\

## 任务

- 目标：验证并冻结 510300.SH 分钟/日频全样本数据链路，产出可回测的冻结快照与字段契约
- 输入：plan.md DEC-001~008 用户裁决；plan_code.md §4 数据需求
- 执行要求：只用局域网 MySQL（-mysql_data/data_driven.py）；幂等抓取；QA 脚本可重跑；跑官方校验器
- 预期输出：data/processed 冻结产物、data-manifest.json、QA 报告、字段字典、验证报告、plan_code.md 数据区块
- 验收标准：QA 全 PASS；validate_mysql_request 与 validate_data_bundle 双 PASS

## 回报

- 完成内容：
  1. 全量抓取并冻结：etf_min 510300.SH（526,825 行 × 2,186 日，2017-01-03..2025-12-31）、fund_daily、
     index_daily 000300.SH、trade_cal、stk_limit、adj_factor（0 行，已确认基金无复权因子）、扩展 ETF 覆盖探针；
  2. QA 冻结脚本 v4：21/21 PASS，0 FAIL，5 警告（均已解释并记录）；
  3. 缺口填充：fund_daily 6 日（分钟聚合）、index_daily 2 日（index_min 聚合，单位换算 元→千元 已实证 999.999）；
  4. 官方校验器：validate_mysql_request PASS（6 查询，含 2025-06 分钟-日历对齐组）、validate_data_bundle PASS（5 数据集）；
  5. 新发现并处置：stk_limit 供应商取整偏差（与 round(pre_close×1.1,0.001) 最大差 0.006，精确匹配 57%）→
     改为合理性区间检查，源值保留为真实涨跌停价；
  6. plan_code.md DATA_AGENT_OWNED 区块已填写（数据集映射 + 8 条读取/对齐规则）。
- 产物路径：
  - data/processed/{minute_bars_510300.parquet, daily_510300.csv, index_daily_000300.csv, trade_calendar.csv,
    limits_daily_510300.csv, tradability.csv, exdiv_days_510300.csv}
  - data/metadata/{data-manifest.json, dt001_qa_report.json, dt001_anchor_checks.csv, field-dictionary.md,
    data-validation.md, mysql-request-spec.json, mysql-request-result.json, validation-spec.json,
    data-bundle-result.json, dt001_fetch.py, dt001_qa_freeze.py}
- 验证证据：QA 21/21 PASS（dt001_qa_report.json）；mysql-request PASS；data-bundle PASS；
  分钟-日频勾稽 close/open 全样本差 0；填充日次日 pre_close 勾稽 8/8 通过。
- 假设与限制：bar 为 END 时间标签（13:00 决策映射 11:30 bar）；2017-08-09 缺竞价 bar（240 根）；
  stk_limit 2019-06-26 前为派生近似；零成交 bar 211 根保留；除息 9 日由 pre_close 口径自动正确。
- 未解决问题：无阻塞项。残余风险：派生涨跌停段（2017-2019H1）的封板标记为近似（该时段 510300 无±10% 极端日，影响可忽略）。
- 建议 next_action：main 验收后推进阶段 4（code_agent 实现 main.ipynb，BLOCK-00~18，按 plan_code.md 与 DATA_AGENT_OWNED 读取规则）。
- log_summary：DT-001 数据链路冻结完成，状态 READY，双官方校验器 PASS。
