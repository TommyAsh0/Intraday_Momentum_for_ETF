# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-003
- stage：code（修订轮二）
- from：code
- to：main
- cycle：3
- status：COMPLETE

## 回报

DEC-012 已实现并干净内核重跑通过（EXECUTION OK，28.7s；增量为 52 万行 1min CSV 落盘）：

1. **BLOCK-10**：`plot_day` 删除 `day_bands_at_taus`，UB/LB 改由 `bands_1m`（= `bands_for` 全 240 列）按 1 分钟全分辨率绘制（`plot` + `fill_between`）；新增图 1/2/4 数据 CSV 的 sigma/UB/LB 列；午休轴（DEC-011）与 VWAP g30 步进线（DEC-009）不变。
2. **BLOCK-03**：新增 `03_noise_bands_1min.csv`——向量化 `UB_1M=max(day_open,pre_close)×(1+VM·SIGMA)`、`LB_1M=min(...)×(1−VM·SIGMA)`，全部 2,186 日 × 240 标签（525,140 行，前 14 日 NaN）；与 `bands_for` 三日一致性断言（2018-06-11 / 2022-04-29 / 2025-06-24，equal_nan 全等）。
3. md 注释与 BLOCK 头注释同步更新（DEC-012）。

不变性自检（对比 review\run_02\sha_after.json 90 文件基线）：82 一致 + 7 有意变更（10_fig1/2/4/5 PNG 与 10_fig1/2/4 数据 CSV）+ 1 新增（03_noise_bands_1min.csv）+ trade_record.csv 逐字节一致；ext 9 冻结输入 mtime 保持 2026-10-05 12:11 未触碰；MISSING 无。

图目检：Fig1/Fig2 的 UB（红）/LB（绿）为逐分钟平滑曲线，开盘窄、午后宽，随 σ 日内形态变化；成交散点与 VWAP 步进线如常；午休轴行为保持。

## 建议

main 验收后派单 CR-003 聚焦复审：1 分钟带独立复算探针、分辨率验证、检查点值=引擎决策值、引擎产物不变性复核。
