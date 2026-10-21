# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CR-002
- stage：code_review（cycle_02，聚焦 CD-002 修订）
- from：main
- to：code_review（本会话无子代理，由 main 亲自执行该角色）
- cycle：2
- status：IN_PROGRESS

## 权限

- work_root：D:\quantitative_project\复现工程\Intraday_Momentum_for_ETF
- 只读路径：main.ipynb、build_nb.py、plan_code.md、data\processed\、output\、trade_record.csv
- 可写路径：work_root\review\cycle_02.md、review\probe_vwap_grid.py、review\run_02\、handoffs\14_code_review_to_main_CR-002.md
- 禁止路径：plan.md、process_log.jsonl、data\processed、source\、output\（审查不得修改被审代码与产物）

## 任务（聚焦三项修订，严于自检）

1. **网格 VWAP 独立复算**（review\probe_vwap_grid.py，不复用 notebook 函数，独立代码路径直读 data\processed\minute_bars_510300.parquet）：
   - 三网格全部决策时点 × 随机 30 日复算 VWAP_g(τ)，与 grids\<g>\04_vwap_check.csv 及引擎语义核对（容差 1e-9）；
   - 专项：13:00 决策点必须用 11:30 bar 及以前；午休（11:30,13:01）不产生 bar；零成交 bar（如 2024-09-27 故障 6 根）不产生增量；2017-08-09 缺竞价 bar 日 VWAP 仍有效；
   - 未来函数：VWAP_g(τ) 不得含标签 τ 之后的 1 分钟 bar（逐项验证：从复算中剔除 τ bar 应得到不同值，含 τ 之后 bar 应得到不同值）。
2. **止损行为抽查**：B-g30 随机 5 笔 CLOSE_LONG/CLOSE_SHORT，独立复算 stop=max(UB,VWAP_g30)/min(LB,VWAP_g30) 与退出时点一致性。
3. **输出契约**：plan_code.md §6 映射（含 grids 新布局）全部文件存在且非空；output\ext\ 未被修订运行改动（与 DT-001 冻结清单比对文件列表）。
4. **隔离重跑确定性**：review\run_02\ 干净内核重跑，关键输出（08_summary_stats、16_cost_sensitivity、09_trade_level_stats、grids/g30 全部、trade_record）sha256 与主线一致。
5. **不变性**：A/B&H 三网格末值与首轮记录一致（A-g30 1,222,781.49 / g15 1,179,990.58 / g05 1,251,402.66；B&H TR 0.6427003365956963）。
6. 官方校验器：validate_trade_record.py 复核。

## 预期输出

- review\cycle_02.md（PASS / REVISION_REQUIRED，问题分级 BLOCKER/MAJOR/MINOR）、review\probe_vwap_grid.py、review\run_02\、handoffs\14 回报

## 回报

（待 code_review 角色填写）
