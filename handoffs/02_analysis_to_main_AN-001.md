# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：AN-001
- stage：paper_planning（PAPER_PLANNING）
- from：analysis（main 亲自执行）
- to：main
- cycle：1
- status：COMPLETE

## 回报

- 完成内容：精读论文 43 页全文（正文、公式、FAQ Q1-Q25、附录表 A1），创建 `plan_code.md`（18 个代码块 BLOCK-00~18、任务清单 32 项、8 个已知缺口）。
- 产物路径：`plan_code.md`
- 验证证据：任务清单覆盖论文主体全部 10 图（Fig 1-10）与 7 表（Table 1-6、A1）；FAQ 25 问中 8 项复现、3 项部分复现、4 项标 NO 并附原因；每个研究块均有 `output\NN_*` 落盘契约与验收锚点。
- 关键方法假设：
  1. 半点决策时点适配 A 股午休：{10:00,10:30,11:00,13:00,13:30,14:00,14:30}，信号用 τ−1 分钟 bar 收盘、成交在 τ bar 开盘，15:00 竞价强制平仓。
  2. 入场须为"新跨越"（止损后不原地立即再入）；反向穿越 = 平仓 + 反手。
  3. 噪声带基准价用 max/min(Open_t, fund_daily.pre_close)，pre_close 含分红除权调整，避免除息日假跳空。
  4. 形态/星期/机制统计基于变体 C 日收益（traded days）；形态判定在 t−1 日完成，无前视。
  5. σ_SPY,t 为 14 日日收益样本 std（ddof=1），显式 shift(1)。
- 数据需求列表：DS-MIN etf_min 510300.SH 2017-01-01~2025-12-31；DS-DAY fund_daily 510300.SH 2016-11-01 起；DS-CAL trade_cal SSE；DS-IDX index_daily 000300.SH；stk_limit/adj_factor（510300，验证用）；扩展 ETF 510500/159915/588000 分钟覆盖（Q12，可选）。
- 未来函数与 A 股迁移风险：rolling 未 shift 风险（BLOCK-02/03 强制 shift）；VWAP 累计口径；ETF 分红除权假跳空；T+1/融券 T+1 → 理论实验；涨跌停以 pre_close±10% 派生或 stk_limit 验证。
- 待 main 裁决的问题：DEC-001~006（标的、样本、时点适配、理论模式、成本模型、VIX 代理），其中成本模型与样本对结论影响最大。
- 建议 next_action：main 固化范围决策并向用户确认 Q-001。
- log_summary：AN-001 完成；plan_code.md 18 块 32 任务全覆盖；待用户裁决 DEC-001~006。
