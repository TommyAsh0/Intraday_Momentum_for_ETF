# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：DT-001
- stage：data_validation
- from：main
- to：data（本会话无子代理，由 main 亲自执行该角色）
- cycle：1
- status：IN_PROGRESS

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：plan.md、plan_code.md、-mysql_data\（data_driven.py / data_driven.md / env\mysql.env 仅封装自动加载）
- 可写路径：work_root\data\、plan_code.md 的 DATA_AGENT_OWNED 区块、handoffs\04_data_to_main_DT-001.md
- 禁止路径：plan.md、process_log.jsonl、main.ipynb、output\、review\、reports\；禁止任何外部数据源（Tushare MCP/网页/TickFlow REST）

## 任务

- 目标：验证局域网 MySQL 对 plan_code.md 全部数据需求的可行性，冻结 production 数据快照，产出 manifest/字段字典/质量报告/tradability，并填写 DATA_AGENT_OWNED 区块。
- 输入：plan_code.md §4 数据需求（DS-MIN etf_min 510300.SH 2016-11-01~2025-12-31；DS-DAY fund_daily；DS-CAL trade_cal SSE；DS-IDX index_daily 000300.SH；stk_limit/adj_factor 验证；扩展 ETF 510500/159915/588000 覆盖探查）。
- 执行要求：
  1. 连接健康检查（trade_cal limit=1），不输出凭据。
  2. 用官方 validate_mysql_request.py 对关键查询做分页核验（无凭据 spec）。
  3. 逐字段核对单位（vol 手/amount 元/分钟 bar 时间戳语义）、实际覆盖、NaN、重复、异常、交易日对齐。
  4. 验证分钟网格：241 bar/日（09:30–11:29、13:00–14:59、15:00 竞价）与标签定义。
  5. 冻结 data\raw（原始快照）与 data\processed（notebook 稳定输入 + 逐分钟 tradability.csv）。
  6. 用 validate_data_bundle.py 对 processed CSV 契约独立检查。
- 预期输出：data\raw\*、data\processed\*、data\metadata\{data-manifest.json, field-dictionary.md, data-validation.md, 校验报告}、plan_code.md DATA_AGENT_OWNED 区块、回报 handoff。
- 验收标准：请求区间完整覆盖或缺口有结构性解释；时间对齐可解释；manifest 状态 complete；校验器 PASS；不得静默缩短区间。

## 回报

（由 04_data_to_main_DT-001.md 承接）
