# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-002
- stage：code_implementation（修订轮）
- from：main
- to：code（本会话无子代理，由 main 亲自执行该角色）
- cycle：2
- status：IN_PROGRESS

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：data\processed\（冻结集）、output\ext\（DT-001 冻结输入）、review\cycle_01.md
- 可写路径：build_nb.py、main.ipynb（由 build_nb.py 重新生成）、output\（除 ext 外可清理重建）、plan_code.md（§6 映射更新）、handoffs\12_code_to_main_CD-002.md
- 禁止路径：plan.md、process_log.jsonl、source\、reports\（报告更新属 AN-003）

## 任务

依据 DEC-009/010/011 三项修订（用户 2026-10-05 裁决）：

1. **BLOCK-04 VWAP 改网格口径**：
   - 网格 bar 划分：每网格 g ∈ {g30,g15,g05}，信号标签序列 = [SIG_BAR.get(τ,τ) for τ in GRIDS[g]] + ["15:00"]；网格 bar k = (前一信号标签, 当前信号标签] 的 1 分钟 bar 区间，首根自 09:30（含竞价 bar）起；午休无 bar 自然跳过；
   - VWAP_g(τ) = Σ_{bar≤τ} close_bar×vol_bar / (Σ vol_bar × 100)，日内累计；零成交 bar 不产生增量；close_bar 为网格 bar 末端 1 分钟 bar 收盘；NaN 收盘 bar 该根贡献置零；
   - 引擎 run_backtest 内部按 grid 取 VWAP_G[grid]（仅信号列有值）；BLOCK-06 止损案例核对同步改；
   - 手工复算：每网格 3 个 (d,τ) 独立标量路径复算 + 每网格随机 20 日全时点导出 `grids\<g>\04_vwap_check.csv`；保留 VWAP(15:00) vs 日均价数量级检查（打印口径）。
2. **输出按网格分类**：
   - 新增 output\grids\g30|g15|g05\；迁入：04_vwap_check、05_oppband_*、06_bandvwap_*、07_dynamic_*（trades/daily_returns/equity，去掉文件名内 _gXX 后缀）、09_round_trips_{A,B,C}；
   - 根目录保留：01/02/03 全系、05_meta/06_meta/07_meta、07_leverage（网格无关）、08_summary_stats、08_alpha_beta、09_trade_level_stats、10 图系、11~18 全系；
   - BLOCK-00 增加运行前清理：删除 OUT 下除 ext 外全部内容并重建 grids 子目录（ext 为 DT-001 冻结输入，禁止触碰）；
   - plan_code.md §6 输出映射表同步更新。
3. **日内图午休轴**：
   - plot_day 及 Fig1/2/4/5 全部改为交易分钟序号横轴（0..239），刻度取真实时刻 {09:31,10:00,10:30,11:00,11:30,13:30,14:00,14:30,15:00}，11:30/13:01 之间画竖虚线并注明午休；
   - 噪声带与 VWAP 以 step(where="post") 画在信号时点位置；成交散点 x = PPos[exec_time]；
   - fig 数据 CSV 增加 minute_idx 与 time 列，vwap 列改为 g30 网格 VWAP 步进值；
   - Q18 日内季节性为类别轴柱状图，无断档缺陷，保持不变。
4. 重跑：python build_nb.py 重新生成 main.ipynb → run_notebook.py 干净内核执行 → validate_trade_record.py 复核；变体 A 与 B&H 不受 VWAP 修订影响，其 g30 末值应与首轮一致（勾稽）；B/C 及全部下游（08/09/11~17 中涉及 B/C 的表）数值允许变化。

## 预期输出

- 修订后 build_nb.py、main.ipynb、output\ 新布局、plan_code.md §6 更新、handoffs\12 回报

## 验收标准

- 干净内核执行通过；流水官方校验 PASS；A-g30/B&H 末值与首轮一致；VWAP 手工复算 assert 全过；grids 目录结构如 DEC-010；图 PNG 全部重新生成且无午休断档

## 回报

（待 code 角色填写）
