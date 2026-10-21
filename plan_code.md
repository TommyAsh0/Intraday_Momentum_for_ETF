# Notebook 代码编写计划

> analysis 创建并维护论文逻辑；data 只能编辑 `DATA_AGENT_OWNED` 区块。本文件描述规格，不记录流程进度。

## 1. 论文与运行信息

- run_id：RUN-001
- 论文：Beat the Market — An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)（Zarattini, Aziz, Barbon；SSRN 4824172；本版 2025-09-22，43 页）
- 目标市场：中国 A 股（上交所 ETF）
- 论文市场：美国，SPY（跟踪 S&P 500）
- 计划样本期：2017-01-01 ~ 2025-12-31（分钟数据实际上限）；日频预热自 2016-11-01
- 频率：1 分钟 bar（**结束时间标签**，DT-001 实证：09:30 开盘竞价 bar + 09:31..11:30 / 13:01..15:00，241 bar/日，无 13:00 标签）+ 日频
- 基准：510300.SH 买入持有（论文即 SPY 自身 B&H）；000300.SH 指数作对照
- 可交易性模式：`EXECUTABLE_WITH_INVENTORY_T0`（用户 2026-10-04 裁决：假设已有底仓可 T+0；先卖后买/先买后卖日内均可合法闭合，前提为底仓+现金缓冲 ≥ 当日交易名义本金；缓冲需求由 BLOCK-18 量化并写入最终报告；涨跌停/停牌仍逐笔核验）

## 2. 研究推理链

论文链条：**噪声带定义 → 突破入场（半点）→ 止损改进（反向带 → 当前带+VWAP）→ 波动率目标动态仓位 → 绩效统计（T1/2/3/A1、T4）→ 稳健性/机制分析（VIX 机制 F8、日内形态 T5、星期效应 T6、波动乘数 F9、RSI-gamma §4.5、成本敏感性 F10）→ FAQ 扩展**。

A 股迁移后的依赖链：

1. 分钟数据（510300.SH）→ 日内时点网格（241 bar/日，END 标签：09:30 开盘竞价 + 09:31–11:30 / 13:01–15:00，DT-001 实证）。
2. 噪声带：每日每时点 τ，前 14 个交易日的 `|Close(τ)/Open(9:30) − 1|` 均值 σ(t,τ)；上带 = max(Open_t, preClose_t)×(1+VM·σ)，下带 = min(Open_t, preClose_t)×(1−VM·σ)。preClose 用 `fund_daily.pre_close`（含分红除权调整），避免除息日假跳空。
3. 信号与交易：决策网格三档（用户 2026-10-04 裁决）：**30 分钟档** τ ∈ {10:00,10:30,11:00,13:00,13:30,14:00,14:30}（论文忠于口径主线）、**15 分钟档** {10:00,10:15,…,11:15,13:00,…,14:45}、**5 分钟档** {10:00,10:05,…,11:25,13:00,…,14:55}；时点 τ 的信息集 = 标签 ≤ τ 的全部 bar（最新价 = 标签 τ bar 收盘，即 τ 时刻刚结束的 1 分钟；午后首个决策 13:00 用 11:30 bar）；成交 = 下一分钟 bar（标签 τ+1；13:00 时为 13:01）开盘价；15:00 收盘强制平仓（15:00 bar 收盘价）。突破入场（仅在"新跨越"时入场，止损后不立即原地再入），反向穿越 = 平仓 + 反手。变体 A/B/C 均在三个网格上全量回测；下游统计（T5/T6/F8/F9/F10/FAQ）以 30 分钟档变体 C 为默认。
4. 三个变体：A=反向带止损+100% 仓位；B=当前带与 VWAP 组合止损（多：max(UB,VWAP)，空：min(LB,VWAP)）+100% 仓位；C=B+动态仓位（σ_target=2% 日波动，杠杆 min(4, σ_target/σ_σ_SPY,t)，σ_SPY,t 为前 14 日收益样本标准差 ddof=1）。
5. 绩效与统计：日收益序列 → T1/2/3/A1 汇总、T4 交易级、alpha/beta 回归（日频 OLS）、F8 波动机制、T5 形态、T6 星期、F9 VM 扫描、§4.5 RSI 回归、F10 成本谱。
6. FAQ 扩展（Q4/Q24 月度表、Q5 多空腿、Q6 lookback 扫描、Q7 最差季度、Q18 日内季节性、Q19 空头 PnL~波动、Q22 VWAP-only、Q23 逐年每笔利润、Q12 多 ETF 简版）。

关键时点纪律：信号形成时点 < 委托时点 = 成交时点（次一分钟 bar 开盘）< 收益实现。无任何同日收盘信号按同一收盘价成交的情形。

## 3. 任务清单

| 任务 ID | 论文图/表/结论记号 | 对应代码块 | 是否可完成 | 逻辑完成置信度 | 备注原因 |
|---|---|---|---|---|---|
| T01 | Figure 1 噪声带概念图 | BLOCK-10 | YES | HIGH | 用真实示例日绘制，概念示意 |
| T02 | Figure 2 两个案例日（2022-01-31 多 / 2022-04-29 空） | BLOCK-10 | YES | HIGH | 同日历日 510300 复刻 |
| T03 | Table 1 变体 A 汇总 + B&H | BLOCK-08 | YES | HIGH | 统计口径见 BLOCK-08 |
| T04 | Figure 3 权益曲线 A vs B&H | BLOCK-10 | YES | HIGH | |
| T05 | Figure 4 案例 2022-01-20 反转日 | BLOCK-10 | YES | MEDIUM | 510300 当日走势与 SPY 不同，仅作同口径案例 |
| T06 | Figure 5 改进止损案例 | BLOCK-10 | YES | MEDIUM | 同 T05 |
| T07 | Table 2 变体 A/B + B&H | BLOCK-08 | YES | HIGH | |
| T08 | Figure 6 权益曲线 A/B/B&H | BLOCK-10 | YES | HIGH | |
| T09 | Table 3 三变体 + B&H | BLOCK-08 | YES | HIGH | |
| T10 | Figure 7 权益曲线含动态仓位 | BLOCK-10 | YES | HIGH | |
| T11 | Table 4 交易级统计 | BLOCK-09 | YES | HIGH | 交易=整趟持仓（round trip） |
| T12 | Table A1 扩展汇总（偏度/最差/最好日） | BLOCK-08 | YES | HIGH | |
| T13 | Figure 8 VIX 开盘分档 Sharpe | BLOCK-11 | PARTIAL | MEDIUM | 无 VIX 数据；用 14 日已实现波动 σ_SPY,t 代理（开盘可得） |
| T14 | Table 5 八种日内形态 | BLOCK-12 | YES | MEDIUM | 形态在 t−1 日频识别 → t 日策略收益（论文未指明时点，取无前视口径） |
| T15 | Table 6 星期效应 | BLOCK-13 | YES | HIGH | |
| T16 | Figure 9 波动乘数 VM 扫描 | BLOCK-14 | YES | HIGH | 每个 VM 全量重跑变体 C |
| T17 | §4.5 RSI(5) 回归 β=-3.25 p=0.001 | BLOCK-15 | YES | HIGH | RSI 用标的日收盘，t−1 时点 |
| T18 | Figure 10 佣金敏感性 | BLOCK-16 | YES | HIGH | 映射为 A 股佣金率×滑点谱 |
| T19 | §4.6 滑点实盘实验（$0.001/股） | — | NO | — | 需实盘下单实验，不可复现；成本敏感性用 T18 替代 |
| T20 | FAQ Q4/Q24 月度收益表 | BLOCK-17 | YES | HIGH | 口径至 2025-12 |
| T21 | FAQ Q5 多空腿权益 | BLOCK-17 | YES | HIGH | |
| T22 | FAQ Q6 lookback 扫描 {5,10,14,20,25,30,60,90} | BLOCK-17 | YES | HIGH | |
| T23 | FAQ Q7 最差 10 季度 | BLOCK-17 | YES | HIGH | 基准换成 510300/000300 季度收益 |
| T24 | FAQ Q12 其他 ETF/个股 | BLOCK-17 | PARTIAL | MEDIUM | 扩展：510500.SH/159915.SZ/588000.SH 变体 C 汇总（分钟数据覆盖待验） |
| T25 | FAQ Q13 期货 33 品种 | — | NO | — | 无期货分钟数据源 |
| T26 | FAQ Q15 I-Star 滑点模型 | — | NO | — | 美股大盘股参数不可移植至 A 股 ETF |
| T27 | FAQ Q18 日内季节性 | BLOCK-17 | YES | MEDIUM | 按成交时点聚合策略 PnL |
| T28 | FAQ Q19 空头 PnL ~ VIX 回归（p=0.91） | BLOCK-17 | PARTIAL | MEDIUM | VIX→σ_SPY,t 代理 |
| T29 | FAQ Q20/Q21 VIX 门槛空头、SMA 过滤 | — | NO | — | FAQ 次级图表 + VIX 缺失；结论文字已知，不做图 |
| T30 | FAQ Q22 VWAP-only 止损变体表 | BLOCK-17 | YES | HIGH | |
| T31 | FAQ Q23 逐年平均每笔利润 | BLOCK-17 | YES | HIGH | |
| T32 | A 股交易约束量化（底仓 T+0 缓冲/涨跌停/停牌/流水） | BLOCK-18 | YES | HIGH | harness 强制交付 + 用户裁决可执行性口径 |
| T33 | 5/15 分钟决策网格变体（用户 2026-10-04 要求） | BLOCK-05~09 | YES | HIGH | A/B/C × {30,15,5}min 全量回测，Tables 1/2/3/4/A1 按网格分列 |

覆盖：论文主体图 10/10、表 7/7（T1-T6+A1）全部有代码块或明确不可完成原因；FAQ 25 问中 8 项复现、3 项部分复现、4 项 NO（T19/T25/T26/T29，原因如上）。

## 4. 数据准备链路

<!-- DATA_AGENT_OWNED_START -->

**状态：READY（2026-10-04 冻结）**。QA 21/21 PASS（`data/metadata/dt001_qa_report.json`）；
官方校验器双 PASS（`mysql-request-result.json`、`data-bundle-result.json`）；
字段与单位详见 `data/metadata/field-dictionary.md`；验证详情见 `data/metadata/data-validation.md`；
sha256 清单见 `data/metadata/data-manifest.json`。

数据集映射（全部位于 `data/processed/`，notebook 用相对路径读取，禁止重查数据库）：

| ID | 文件 | 内容 |
| --- | --- | --- |
| DS-MIN | `minute_bars_510300.parquet` | 510300.SH 1 分钟 bar，526,825 行 × 2,186 日（2017-01-03..2025-12-31） |
| DS-DAY | `daily_510300.csv` | 510300.SH 日线 2,230 行（含 6 个 `minute_filled` 填充日），含 `pre_close`、`pct_chg`、`ret` |
| DS-IDX | `index_daily_000300.csv` | 000300.SH 日线 2,230 行（含 2 个 `index_min_filled` 填充日），仅作对照基准 |
| DS-CAL | `trade_calendar.csv` | SSE 日历 2016-11-01..2025-12-31 |
| DS-LIMIT | `limits_daily_510300.csv` | 涨跌停价（2019-06-26 前为派生近似，见 `limit_source`） |
| DS-TRADABILITY | `tradability.csv` | 分钟级可买/可卖/封板标记（harness 字段契约） |
| DS-EXDIV | `exdiv_days_510300.csv` | 9 个除息日及隐含每股分红 |

给 code 角色的读取与对齐规则（必须遵守）：

1. **bar 语义**：`09:30` 为开盘集合竞价 bar；`09:31..11:30`、`13:01..15:00` 为结束时间标签的 1 分钟 bar；
   无 13:00 标签。决策时点 τ 信号价 = 标签 τ bar 的 close；τ=13:00 用 11:30 bar（`signal_bar` 映射）。
   成交价 = 下一分钟 bar（τ+1；13:00 时为 13:01）的 open。15:00 平仓价 = 15:00 bar close（= 日线 close）。
   日 Open = 09:30 bar open；2017-08-09 缺竞价 bar，Open 取 09:31 bar open（全日 240 根）。
2. **pre_close 口径**：噪声带基准 preClose 用 DS-DAY `pre_close`（除息调整口径，开盘前可得）；
   日收益用 `ret`（= pct_chg/100，含分红）。禁止使用 adj_factor（基金无数据）或自行复权。
3. **不完整日**：2017-08-09（240 bar）保留参与回测，引擎不得假设 09:30 bar 存在（用当日首根 bar）。
4. **除息日**：9 天（DS-EXDIV）无需特判——噪声带用 pre_close 后已自动正确；分钟价为未复权市价，与 pre_close 同口径。
5. **涨跌停**：DS-LIMIT 2019-06-26 前为 `round(pre_close×1.1,0.001)` 派生值（与源值最大偏差 0.006 元）；
   封板判断用 DS-TRADABILITY 的 `可买/可卖/涨停封板/跌停封板` 列（全样本涨停封板仅 8 分钟、跌停 0 分钟）。
6. **单位**：分钟 vol 手、amount 元 → VWAP = 累计 amount/(累计 vol×100)；日线 amount 千元。
   份额取整 `floor(…/100)×100`。
7. **预热**：σ(t,τ) 需前 14 个交易日的 |Close(τ)/Open−1| 序列 → 样本前 14 个交易日不产生信号
   （σ_SPY,t 同理 shift(1) 后前 14 日 NaN，不交易、不持仓）。
8. **索引基准**：DS-IDX 仅用于对照权益线/季度对比；策略信号与成交全部只用 DS-MIN/DS-DAY。

<!-- DATA_AGENT_OWNED_END -->

## 5. Notebook 代码块

### BLOCK-00：配置与公共函数

- 类型：`CODE`（NO_ARTIFACT）
- 对应任务：全部
- 研究目的：集中参数、路径、常量与公共函数。
- 公式与参数：`LOOKBACK=14`、`VOL_MULT=1.0`、`SIGMA_TARGET=0.02`、`MAX_LEV=4`、`INIT_CAPITAL=1_000_000`、`COMMISSION_RATE=0.0001`（万1/边）、`SLIPPAGE_TICK=0.001`（¥/份/边）、`LOT=100`、决策网格 `GRIDS={'g30':[10:00,10:30,11:00,13:00,13:30,14:00,14:30], 'g15':[10:00,…,14:45 步长15分], 'g05':[10:00,…,14:55 步长5分]}`、样本 `2017-01-01~2025-12-31`、随机种子固定（本策略无随机性，仅防御）。
- 计算步骤：imports；路径（全部相对 work_root）；常量；公共函数（读冻结 parquet/csv、分钟网格构造、绩效统计函数、OLS 封装）。
- 落盘输出：无（NO_ARTIFACT，仅辅助）。
- 验收：notebook 从干净内核可导入执行。

### BLOCK-01：数据加载与分钟网格验证

- 类型：`CODE`
- 对应任务：全部（数据底座）
- 论文位置：§2 Data（1 分钟 OHLCV，IQFeed → 本地 MySQL etf_min）
- 研究目的：加载冻结分钟/日频快照，验证网格完整性，与日频交叉锚定。
- 输入数据集 ID：DS-MIN（etf_min 510300.SH）、DS-DAY（fund_daily）、DS-CAL（trade_cal SSE）、DS-IDX（index_daily 000300.SH）
- 输入字段、主键、单位：`trade_time, open, high, low, close, vol(手), amount(元)`；`trade_date, open/close/pre_close/pct_chg/vol(手)/amount(千元)`
- 信息最晚可得时点：全部为历史行情，无时点问题；`pre_close` 在当日开盘前可得。
- 计算步骤：
  1. 读冻结文件；按 `trade_time` 排序；派生 `trade_date`、bar 标签 `HH:MM`。
  2. 校验每日 bar 数（标准 241：09:30 竞价 1、09:31–11:30 共 120、13:01–15:00 共 120，END 标签）与标签集合。
  3. 聚合分钟 → 日 open（09:30 bar open）、close（15:00 bar close，缺则用最后 bar）、high/low/vol/amount，与 fund_daily 逐日比对。
  4. 至少 3 个随机日期锚点人工级核对（分钟 close 与日频一致）。
- NaN 与异常处理：缺 bar 日记录清单；全天 <200 bar 或缺 09:30/15:00 bar 的日列入 `01_incomplete_days.csv`（交易跳过，见 BLOCK-05）。
- 未来函数风险：无（纯数据校验）。
- notebook 展示：覆盖区间、交易日数、bar 数分布、与日频 close 最大绝对差。
- 落盘输出：`output\01_data_overview.json`、`output\01_daily_crosscheck.csv`、`output\01_incomplete_days.csv`
- 输出 schema/粒度：overview=键值 JSON；crosscheck=每交易日一行（分钟聚合 vs fund_daily 各字段与差值）。
- 预期数值或形态：交易日约 2180±30；close 差值 ≈ 0（<0.001 元或记录原因）。
- 验收方法：行数与日期范围符合 manifest；锚点差值在 rounding 内；不完整日清单非空时逐日有原因。
- 失败处理：任何锚点不一致 >0.01 元 → 停止并报告 main。

### BLOCK-02：日频序列与 σ_SPY,t

- 类型：`CODE`
- 对应任务：T03/T07/T09/T12（B&H 基准、动态仓位波动输入）、T17
- 论文位置：§3（σ_SPY,t 定义，p.15）
- 研究目的：构造日收益与 14 日样本波动（动态仓位输入），生成 B&H 基准净值。
- 公式与参数：`ret_d = pct_chg/100`（fund_daily，含分红调整口径）；`σ_SPY,t = sqrt(1/13 · Σ_{i=1..14}(ret_{t-i} − μ_t)²)`，`μ_t = (1/14)Σ ret_{t-i}`；B&H 净值 = Π(1+ret)。
- 输入数据集 ID：DS-DAY
- 信息最晚可得时点：σ_SPY,t 用 t−1 及以前日收益，开盘前可得。
- 计算步骤：按交易日排序 → 日收益 → rolling(14) 样本 std（ddof=1，显式 shift(1) 对齐到 t 日开盘可得）→ B&H 净值（样本期内，初值 1）。
- NaN 与异常处理：预热期（前 14 个交易日）σ 为 NaN，动态仓位回测从第 15 个交易日起；记录剔除日数。
- 未来函数风险：rolling 未 shift 会泄露当日收益 —— 必须 shift(1) 后参与 t 日仓位。
- 落盘输出：`output\02_daily_series.csv`（date, open, close, pre_close, ret, sigma14, bh_nav）
- 验收方法：抽 3 日手工复算 σ_SPY,t（误差 <1e-10）；B&H 净值末日 = Π(1+ret) 直接复算一致。

### BLOCK-03：噪声带（Noise Area）

- 类型：`CODE`
- 对应任务：T01/T02 及全部策略块
- 论文位置：§3，公式 1-4（p.6-7）与 §4.4（VM，p.21）
- 研究目的：计算每个交易日、每个分钟时点 τ 的 σ(t,τ) 与上下带。
- 公式与参数：`move_{d,τ} = |Close_{d,τ}/Open_{d,9:30} − 1|`；`σ_{t,τ} = mean_{i=1..14} move_{t-i,τ}`；`UB = max(Open_t, preClose_t)·(1+VM·σ_{t,τ})`，`LB = min(Open_t, preClose_t)·(1−VM·σ_{t,τ})`。
- 输入数据集 ID：DS-MIN（派生每分钟末价格网格）、DS-DAY（pre_close）
- 输入字段、主键、单位：价格元；τ 网格 = 每分钟的"价格时点"（09:31…11:30、13:01…15:00，END 标签下 price(τ) = 标签 τ bar 的 close，即 τ 时刻刚完成 bar 的收盘；15:00 用收盘 bar）。
- 信息最晚可得时点：σ_{t,τ} 用前 14 个完整交易日，t 日开盘前可得；UB/LB 的 max/min(Open_t, preClose_t) 在 09:30 bar 收盘后（09:31）可得，首个决策 10:00 合法。
- 信号/委托/成交/收益区间：本块只产出带，不交易。
- 计算步骤：
  1. 构造日 × τ 价格矩阵 P[d,τ] 与开盘价向量 Open_d。
  2. move 矩阵 → 对每列 τ 做 rolling(14).mean() 且 shift(1)（t 日只用 t−1 及以前）。
  3. 逐日合成 UB/LB（VM=1 基准；VM 扫描在 BLOCK-14 复用本块函数）。
- NaN 与异常处理：样本前 14 个交易日 σ 为 NaN（无带，不交易）；不完整日的 move 按可得 τ 计算并在清单标注。
- 未来函数风险：rolling 不 shift 会包含当日 move —— 必须 shift(1)。
- notebook 展示：σ 随 τ 的均值形态（应单调上升至尾盘）；示例日带图数据。
- 落盘输出：`output\03_noise_bands_sample.csv`（全部日 × 决策时点 + 15:00 的 σ/UB/LB）、`output\03_sigma_shape.csv`（σ 按时点全样本均值）
- 预期形态：σ(τ) 随 τ 递增；数值量级 0.1%~2%。
- 验收方法：抽 3 个 (d,τ) 手工复算 move 与 σ（误差 <1e-12）；检查 t 日行不包含 t 日 move。
- 失败处理：网格缺列致 σ 大面积 NaN → 停止报告。

### BLOCK-04：VWAP

- 类型：`CODE`
- 对应任务：T07/T09（变体 B/C 止损）
- 论文位置：§3 脚注 2（VWAP 仅用市场交易时段数据）
- 公式与参数（CD-002 修订，DEC-009，用户 2026-10-05 裁决）：VWAP 按**决策间隔 bar** 聚合——网格 bar =（前一信号标签, 当前信号标签] 的 1 分钟 bar 合计（首根自 09:30 含竞价 bar 起；13:00 用 11:30 bar；午休无 bar 自然跳过）；`VWAP_{g,τ} = Σ_{bar≤τ} close_bar×vol_bar / (Σ vol_bar × 100)`（close_bar 为网格 bar 末端收盘、vol 手 → 份）。每网格 g ∈ {g30,g15,g05} 独立计算，引擎按 grid 取用。
- 计算步骤：按网格聚合 bar 量/收盘 → 日内累计 Σclose×vol、Σvol → 仅信号列取值；零成交 bar 不产生增量；NaN 收盘 bar 该根贡献置零。
- NaN 与异常处理：vol=0 的 bar 不产生增量；整日 vol=0 → 当日 VWAP NaN，当日不交易（计入清单）。
- 未来函数风险：必须用截至 τ 的累计，不用全天累计。
- 落盘输出：`output\04_vwap_check.csv`（抽 20 日 × 决策时点的 VWAP 与独立复算值）
- 验收方法：抽 3 个 (d,τ) 手工复算（误差 <1e-9）；与日频 amount/vol 平均价数量级一致。

### BLOCK-05：回测引擎与变体 A（Opposite Band）

- 类型：`CODE`
- 对应任务：T03/T04/T05/T11/T12
- 论文位置：§3（入场/止损/平仓、p.9-10；仓位公式 p.10）
- 研究目的：实现统一回测引擎并跑变体 A：100% 仓位、止损=反向带（等价于反向穿越反手）。
- 公式与参数：`Shares_t = floor(AUM_{t-1} / Open_t / 100) × 100`（整手）；成本 = 佣金 rate×成交额 + 滑点 tick×份额，双边。
- 交易规则（引擎规格，三种止损模式参数化，决策网格 `grid ∈ {g30,g15,g05}` 参数化）：
  1. 决策时点 τ ∈ grid（默认 g30 = {10:00,10:30,11:00,13:00,13:30,14:00,14:30}）；信息价格 p(τ) = 标签 τ bar 收盘价（τ 时刻刚完成的 1 分钟 bar；13:00 用 11:30 bar）；成交价 = 下一分钟 bar（标签 τ+1；13:00 时为 13:01）开盘价（15:00 平仓 = 15:00 bar 收盘价）。
  2. 空仓且价格新跨越上带（前一决策时点价格 ≤ UB）→ 买入开多；新跨越下带 → 卖出开空。
  3. 变体 A 持多期间：价格 < LB → 平多并反手开空（同一时点两笔成交）；对称同理。
  4. 15:00 强制平仓（当日剩余持仓）。
  5. 空仓再入场必须满足"新跨越"（记录前一决策时点相对带位置）。
- 资金核算：逐笔现金流水；AUM_t = AUM_{t-1} + Σ当日净盈亏（含成本）；日收益 = AUM 变动 / AUM_{t-1}；权益非负检查（≤0 则停止报错）。**每个网格独立核算一条资金线**（三个网格各自从 ¥1,000,000 起）。
- NaN 与异常处理：不完整日/无带日不交易；bar 缺失致成交价 NaN → 当日不交易并记录。
- 未来函数风险：成交价严格晚于信号价 1 分钟；15:00 平仓价当日可得（收盘成交）。
- A 股规则限制：无底仓时 T+1 下当日买入不可当日卖出；按用户裁决假设已有底仓可 T+0，所需底仓/现金缓冲由 BLOCK-18 量化。
- notebook 展示：交易笔数、首日/末日 AUM、日收益前 5 行。
- 落盘输出：`output\05_oppband_trades_g30.csv`、`05_oppband_daily_returns_g30.csv`、`05_oppband_equity_g30.csv`（g15/g05 同构同名后缀）、`output\05_meta.json`
- 输出 schema：trades=每笔一行（date, decision_time, exec_time, side, price, shares, cost, pnl_after_close, trade_id 串联整趟, grid）；daily=每交易日一行；equity=日净值。
- 验收方法：抽 3 笔手工复算成交价/成本/盈亏；交易笔数与日收益行数勾稽；现金账连续性（AUM 递推误差 <1e-6）；g15/g05 网格决策时点集合合规（均在交易时段内）。

### BLOCK-06：变体 B（Current Band + VWAP）

- 类型：`CODE`
- 对应任务：T07/T08/T11/T12
- 论文位置：§3（p.12-13）：Long TrailingStop = max(UB, VWAP)；Short = min(LB, VWAP)
- 与 BLOCK-05 关系：同引擎，止损模式参数切换。
- 交易规则差异：持多时价格 < max(UB, VWAP) → 平仓（若同时 < LB 则平仓+反手）；止损后不立即原地再入（需新跨越）。
- 落盘输出：`output\06_bandvwap_trades_g30.csv`、`06_bandvwap_daily_returns_g30.csv`、`06_bandvwap_equity_g30.csv`（g15/g05 同构同名后缀）、`output\06_meta.json`
- 验收：抽 3 个止损案例核对 VWAP/带取值与成交价；交易笔数 ≥ 变体 A（更紧止损 → 更多交易，方向性检查，逐网格验证）。

### BLOCK-07：变体 C（B + 动态仓位）

- 类型：`CODE`
- 对应任务：T09/T10/T11/T12 及后续全部统计（论文默认分析变体）
- 论文位置：§3（p.15）：`Shares_t = floor(AUM_{t-1} × min(4, σ_target/σ_SPY,t) / Open_t)`；杠杆上限 4x
- 计算步骤：读 BLOCK-02 的 σ_SPY,t（已 shift）；lev_t = min(4, 0.02/σ_SPY,t)；份额整手化；其余同变体 B。**在 g30/g15/g05 三个网格各自独立回测**；g30 为论文主线，g15/g05 为用户要求的决策频率变体（T33）。
- NaN：σ_SPY,t NaN 日（预热期）不交易。
- 落盘输出：`output\07_dynamic_trades_g30.csv`、`07_dynamic_daily_returns_g30.csv`、`07_dynamic_equity_g30.csv`（g15/g05 同构同名后缀）、`output\07_leverage.csv`、`output\07_meta.json`
- 验收：抽 3 日手工复算 lev 与份额；lev ∈ (0,4] 全覆盖检查；权益非负；g15/g05 交易笔数通常多于 g30（更密决策 → 更多触发，方向性检查）。

### BLOCK-08：汇总统计 Tables 1/2/3/A1 + Alpha/Beta

- 类型：`CODE`
- 对应任务：T03/T07/T09/T12
- 论文位置：Table 1/2/3（p.11/14/15）、Table A1（p.43）、回归式（p.15-16）
- 公式与参数：Total Return = 末/初−1；IRR = (1+TR)^(252/N)−1；Vol = std(日收益)×√252；Sharpe = mean/std×√252（rf=0）；Hit Ratio = 正收益日占比（全样本日口径为主，附 traded-days 口径）；MDD 基于日净值；Skewness 日收益偏度；Worst/Best Day；`RetMom,t = α + β·RetETF,t + ε`（日频 OLS，α 年化 ×252，报告 t 值）。
- 输入：05/06/07 daily_returns + equity（全部三档网格）+ BLOCK-02 日收益。
- 落盘输出：`output\08_summary_stats.csv`（行=变体{A,B,C}×网格{g30,g15,g05}+B&H，列=全部指标；g30 为论文主线口径）、`output\08_alpha_beta.csv`（α/β/t/p/N/年化α，按变体×网格）
- 验收：用 equity 独立复算 Total Return/MDD 一致；回归样本数与日收益行数一致。

### BLOCK-09：交易级统计 Table 4

- 类型：`CODE`
- 对应任务：T11
- 论文位置：Table 4（p.16）：Trades、Avg Trade×Day、Hit Ratio、Avg PnL×Share、Max Loss/Gain Trade（含日期）
- 口径：trade = 整趟持仓（开→平）；PnL/Share = 整趟净盈亏/份额（含成本）；Max Loss/Gain 按整趟收益率（%，对名义本金）。
- 落盘输出：`output\09_trade_level_stats.csv`（行=变体×网格）
- 验收：trades 数 = trades 文件整趟数；hit 与逐趟盈亏符号一致；抽 2 趟复算。

### BLOCK-10：全部图形（Fig 1-7）

- 类型：`CODE`
- 对应任务：T01/T02/T04/T05/T06/T08/T10
- 论文位置：Fig 1（p.8）、Fig 2（p.9，2022-01-31/2022-04-29）、Fig 3（p.11）、Fig 4-5（p.12-13，2022-01-20）、Fig 6（p.14）、Fig 7（p.16）
- 计算步骤：权益曲线三图（含绘图数据 csv）；案例日图：价格线 + UB/LB 带 + VWAP + 成交标记（2022-01-31、2022-04-29、2022-01-20 三日，510300 实际数据）；Fig 1 概念图用 2022-01-31 简化呈现。
- 落盘输出：`output\10_fig1_concept.png`、`10_fig2_case_days.png`、`10_fig3_equity_oppband.png`、`10_fig4_case_20220120.png`、`10_fig5_stops_20220120.png`、`10_fig6_equity_ab.png`、`10_fig7_equity_abc.png` 及对应 `_data.csv`
- 验收：图形数据 csv 与 trades/bands 一致；图非空、轴标签完整。

### BLOCK-11：Figure 8 波动机制（σ_SPY 代理）

- 类型：`CODE`
- 对应任务：T13（PARTIAL）
- 论文位置：§4.1 + Fig 8（p.17-18）：VIX 开盘分档 → 各门槛以上日的策略 Sharpe
- 替代口径：以 σ_SPY,t（14 日日收益 std，开盘前可得）分档，如 {0, 0.5%, 0.75%, 1%, 1.25%, 1.5%, 2%, 2.5%, 3%}，对每个门槛计算变体 C 日收益（traded days）的 Sharpe。
- 落盘输出：`output\11_vol_regime_sharpe.csv`、`output\11_fig8_vol_regime.png`
- 预期：论文形态为 Sharpe 随波动上升（VIX>40 后回落）；A 股结论如实记录。
- 验收：各档日数与 σ_SPY 分布一致；与论文差异在报告中解释（代理变量不同）。

### BLOCK-12：Table 5 日内形态

- 类型：`CODE`
- 对应任务：T14
- 论文位置：§4.2 + Table 5（p.18-19）
- 口径（无前视）：形态用 t−1 及以前日频 OHLC（fund_daily）判定，统计 t 日变体 C 策略收益（traded days）。
- 形态定义（严格按论文文字）：
  - NR4/NR7：range(t−1) 为最近 4/7 日最小（range = high−low）。
  - ID：high(t−1) < high(t−2) 且 low(t−1) > low(t−2)。
  - OD：high(t−1) > high(t−2) 且 low(t−1) < low(t−2)。
  - Triangle：high(t−1) 低于前 2 日高点且 low(t−1) 高于前 2 日低点。
  - Trend Day：open 在日 range 的 15% 分位以下且 close 在 85% 分位以上（反向为看空），且 range(t−1) > 14 日平均 range。
  - Big Tail：open 与 close 同时在日 range 顶部 75% 以上（hammer）或同时在底部 25% 以下（reverse hammer）。
  - Strong/Weak Closure：close 在日 range 的 90% 分位以上或 10% 分位以下。
- 输出：Unconditional + 8 形态的 Observations、Avg PnL(bps)、t-stat、Hit Ratio、Sharpe。
- 落盘输出：`output\12_daily_patterns.csv`
- 验收：抽 2 日手工验证 NR4/ID 判定；各形态日数与定义自洽；t 值 = mean/(std/√N)。

### BLOCK-13：Table 6 星期效应

- 类型：`CODE`
- 对应任务：T15
- 论文位置：§4.3 + Table 6（p.20-21）
- 口径：变体 C 日收益按星期分组（traded days），输出 Observations/Avg bps/t-stat/Hit/Sharpe。
- 落盘输出：`output\13_day_of_week.csv`
- 验收：5 组日数之和 = traded days 总数。

### BLOCK-14：Figure 9 波动乘数 VM 扫描

- 类型：`CODE`
- 对应任务：T16
- 论文位置：§4.4 + Fig 9（p.21-22）：VM ∈ 约 0.2~3；最优 Sharpe ≈ VM 1.5；总收益随 VM 递减
- 口径：VM ∈ {0.2,0.4,…,2.4} 共 12 档，每档全量重跑变体 C（复用 BLOCK-03/05 函数），输出 Sharpe 与 Total Return 双条形图。
- 落盘输出：`output\14_vm_sweep.csv`、`output\14_fig9_vm_sweep.png`
- 验收：VM=1 行与 BLOCK-08 变体 C 指标一致（锚点）。

### BLOCK-15：§4.5 RSI 回归

- 类型：`CODE`
- 对应任务：T17
- 论文位置：§4.5（p.23-24）：`RetMom,t(bps) = α + β·RSI_SPY,t−1 + ε`；论文 β=-3.25，p=0.001
- 口径：RSI(5) 用标的日收盘（Wilder 或 Cutler 口径需在代码注明，基准用 Wilder）；自变量 t−1 收盘可得；因变量变体 C 日收益（bps，全样本日，无交易日=0）。
- 落盘输出：`output\15_rsi_regression.csv`（α/β/t/p/N/R²）
- 验收：回归 N = 日收益行数（扣 RSI 预热）；抽 3 日手工复算 RSI。

### BLOCK-16：Figure 10 成本敏感性

- 类型：`CODE`
- 对应任务：T18
- 论文位置：§4.6 + Fig 10（p.24-25）
- 口径：佣金率谱 {0, 0.005%, 0.01%, 0.02%, 0.03%} × 滑点 {0, 1, 2} tick 重跑变体 C，画 Total Return 曲线（主图：固定 1 tick 滑点，佣金谱）。
- 落盘输出：`output\16_cost_sensitivity.csv`、`output\16_fig10_cost.png`
- 验收：零成本行与 BLOCK-07 毛结果勾稽；成本单调性检查。

### BLOCK-17：FAQ 扩展

- 类型：`CODE`
- 对应任务：T20/T21/T22/T23/T24/T27/T28/T30/T31
- 计算步骤（变体 C 为主，复用引擎）：
  1. Q4/Q24：月度与年度收益表（至 2025-12）。
  2. Q5：仅多/仅空/双边三条权益线（每趟盈亏按方向拆分）。
  3. Q6：lookback ∈ {5,10,14,20,25,30,60,90} 全量重跑汇总表。
  4. Q7：510300 季度收益最差 10 季度 vs 策略同季度收益。
  5. Q18：按成交时点（决策时点）聚合平均每笔 PnL 的日内形态图。
  6. Q19：空头整趟 PnL(bps) ~ 当日 σ_SPY,t 回归（论文用 VIX，p=0.91 不显著）。
  7. Q22：VWAP-only 止损变体全量重跑，汇总表（对应论文 Q22 表口径：Total/IRR/Vol/Sharpe/Hit/MDD）。
  8. Q23：逐年平均每笔 PnL/Share。
  9. Q12（PARTIAL）：510500.SH/159915.SZ/588000.SH 变体 C 汇总指标（若分钟数据覆盖不足则在报告中标注）。
- 落盘输出：`output\17_monthly_table.csv`、`17_long_short_legs.csv/.png`、`17_lookback_sweep.csv`、`17_worst_quarters.csv`、`17_intraday_seasonality.csv/.png`、`17_short_pnl_vol_regression.csv`、`17_vwap_only_stats.csv`、`17_profit_per_share_by_year.csv/.png`、`17_other_etfs.csv`
- 验收：月度表行数 = 样本月数；lookback=14 行与 BLOCK-08 一致；VWAP-only 交易笔数 < 变体 B/C（论文方向：更少交易）。

### BLOCK-18：标准交易流水与 A 股约束量化

- 类型：`CODE`
- 对应任务：T32
- 论文位置：无（harness 强制）
- 计算步骤：
  1. 由变体 C（g30 主线）生成 `trade_record.csv`（UTF-8；前八列固定：交易日期,交易时间,股票代码,股票名称,交易价格,交易数量,交易方向,交易标识；附加审计列：信号时间,止损类型,佣金,滑点,费用合计,杠杆,策略变体,run_id）。
  2. 生成/核对 `data\processed\tradability.csv`（每个成交时点的 是否交易日/停牌/有成交/可买/可卖/涨停价/跌停价，由 data 交付，code 只做一致性引用）。
  3. 运行官方校验器 `validate_trade_record.py`（含 ≥3 探针：普通时点、涨停日、15:00 竞价时点）。
  4. 底仓 T+0 可执行性量化（用户 2026-10-04 裁决口径）：统计每日交易名义本金/AUM（=杠杆分布），给出所需底仓+现金缓冲倍数（多头腿需现金缓冲、空头腿需底仓缓冲，各 ≥ 当日名义本金）；逐笔核验涨跌停/停牌可成交性；说明无底仓情形下的 T+1 违规占比作为对照。
- 落盘输出：`trade_record.csv`、`output\18_ashare_constraints.json`、`output\18_trade_validation.json`
- 验收：官方校验器 PASS；约束统计与流水行数一致。

## 6. 代码块—产物—论文映射

| BLOCK | 任务 ID | 论文图/表/结论 | 输出文件 | 绘图基础数据 | 验收锚点 |
|---|---|---|---|---|---|
| 00 | 全部 | — | NO_ARTIFACT | — | 干净内核可跑 |
| 01 | 全部 | §2 Data | 01_data_overview.json 等 | — | 3 锚点比对 |
| 02 | T03/07/09/12/17 | p.15 σ_SPY | 02_daily_series.csv | — | 3 日手工复算 σ |
| 03 | T01/02 全部策略 | §3 式 1-4 | 03_noise_bands_sample.csv、03_noise_bands_1min.csv（全部日 × 240 个 1 分钟时点，DEC-012）、03_sigma_shape.csv | — | 3 (d,τ) 手工复算 |
| 04 | T07/09 | §3 脚注 2 | grids\<g>\04_vwap_check.csv（每网格，DEC-009 网格口径） | — | 每网格 3 (d,τ) 手工复算 |
| 05 | T03/04/05/11/12 | §3 base | grids\<g>\05_oppband_{trades,daily_returns,equity}.csv（DEC-010） | — | 3 笔手工复算 |
| 06 | T07/08/11/12 | §3 p.12-13 | grids\<g>\06_bandvwap_* | — | 止损案例核对 |
| 07 | T09~12 等 | §3 p.15 | grids\<g>\07_dynamic_*、07_leverage.csv（根目录） | — | 3 日 lev 复算 |
| 08 | T03/07/09/12 | Tables 1/2/3/A1 | 08_summary_stats.csv | — | equity 复算勾稽 |
| 09 | T11 | Table 4 | grids\<g>\09_round_trips_{A,B,C}.csv、09_trade_level_stats.csv（根目录） | — | 整趟数勾稽 |
| 10 | T01/02/04/05/06/08/10 | Fig 1-7 | 10_fig*.png（交易分钟轴、午休剔除，DEC-011；噪声带 1 分钟全分辨率，DEC-012） | 10_*_data.csv | 图数一致 |
| 11 | T13 | Fig 8 | 11_vol_regime_sharpe.csv | 11_*_data.csv | 档数勾稽 |
| 12 | T14 | Table 5 | 12_daily_patterns.csv | — | 2 日形态手工验证 |
| 13 | T15 | Table 6 | 13_day_of_week.csv | — | 组数和勾稽 |
| 14 | T16 | Fig 9 | 14_vm_sweep.csv | 同 csv | VM=1 锚点 |
| 15 | T17 | §4.5 | 15_rsi_regression.csv、15_rsi_regression_zero_cost.csv + 15_rsi_zero_cost_daily.csv（零成本 A/B/C，DEC-014） | — | N 勾稽 |
| 16 | T18 | Fig 10 | 16_cost_sensitivity.csv、16_cost_w1_zero_slip.csv（三变体零滑点万1对照，DEC-013）、16_fig10_cost.png | 同 csv | 零成本锚点 |
| 17 | T20-24/27/28/30/31 | FAQ Q4-Q23 | 17_* | 17_*_data.csv | 月数/lookback 锚点 |
| 18 | T32 | harness | trade_record.csv、18_* | — | 官方校验器 PASS |

## 7. 标准交易流水

- 是否存在交易实验：是（底仓 T+0 假设下的可执行回测）
- 交易标的：510300.SH 沪深300ETF华泰柏瑞
- 信号时点：决策网格 g30/g15/g05（信息截至标签 τ bar 收盘，即 τ 时刻刚完成的 bar；13:00 用 11:30 bar）；主流水为 g30
- 最早合法成交时点：下一分钟 bar（标签 τ+1；13:00 时为 13:01）开盘价；日终 15:00 bar 收盘平仓
- 100 股整手规则：份额 = floor(名义/Open/100)×100
- T+1 与底仓 T+0（用户 2026-10-04 裁决）：假设账户已持有足额底仓与现金缓冲——多头腿"先买（现金）后卖（旧份额）"、空头腿"先卖（底仓）后买（资金回笼）"日内均可合法闭合；BLOCK-18 量化所需缓冲倍数（逐日名义本金/AUM）并给出无底仓对照；融券不使用（空头腿走底仓卖出）
- 涨跌停/无涨跌幅限制阶段/停牌/ST/板块：510300 为主板 ETF，±10% 涨跌停（逐日 stk_limit 或由 pre_close±10% 派生，data 验证）；ETF 无 ST；停牌以缺 bar 识别
- 成本：佣金 0.01%/边（ETF 免印花税）；滑点 ¥0.001/份/边（1 个最小价位）；敏感性谱见 BLOCK-16
- 做空/融券：空头腿以底仓卖出实现，不涉融券；无底仓对照在 BLOCK-18 说明
- `trade_record.csv` 附加审计列：信号时间,止损类型,佣金,滑点,费用合计,杠杆,策略变体,run_id

## 8. 已知缺口与替代方案

| 缺口 ID | 影响任务 | 原因 | 可选方案 | 对结论影响 | 需 main/用户裁决 |
|---|---|---|---|---|---|
| GAP-01 | T13/T28 | 无 VIX 数据 | 用 σ_SPY,t（14 日已实现波动）代理，开盘可得 | 机制分析口径变化，方向性结论仍可做 | 是（DEC-006） |
| GAP-02 | T19 | 滑点实盘实验不可复现 | 需真实下单 | 以佣金×滑点敏感性谱替代（T18） | 否 |
| GAP-03 | T25/T26/T29 | 期货数据/I-Star 参数/VIX 条件图 | 数据源缺失或参数不可移植 | FAQ 次级内容，不影响主结论 | 否 |
| GAP-04 | 全部 | 论文样本 2007-2024（17 年，SPY） vs 本地 2017-2025（9 年，510300） | 分钟数据覆盖上限 | 数值不可直接比，只比方向与结构 | 是（DEC-002） |
| GAP-05 | 交易执行 | A 股 ETF 二级市场 T+1、融券 T+1 还券 | 用户裁决：假设已有底仓可 T+0；BLOCK-18 量化所需底仓/现金缓冲倍数并给无底仓对照 | 缓冲充足时可执行；缓冲不足的高杠杆日须降杠杆或放弃交易 | 已裁决（DEC-004，2026-10-04） |
