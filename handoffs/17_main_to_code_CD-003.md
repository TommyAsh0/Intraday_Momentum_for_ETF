# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CD-003
- stage：code（修订轮二）
- from：main
- to：code
- cycle：3
- status：IN_PROGRESS

## 任务单

用户 Q-003 裁决（2026-10-05）：日内图中 UB/LB 呈半小时步进直线，系绘图按 g30 检查点抽样连线所致；论文 §3 的 UpperBound_{t,τ} 之 τ 为 1 分钟离散时点，噪声带应逐分钟绘制。固化为 DEC-012。

实现范围（仅 BLOCK-03 输出与 BLOCK-10 图形，引擎零改动）：

1. BLOCK-10 `plot_day`：删除 `day_bands_at_taus`（g30 检查点抽样 + step 连线），改用全 240 列 `bands_for` 结果按 1 分钟全分辨率 `plot/fill_between`；DEC-011 午休轴与 DEC-009 VWAP g30 步进线语义保持不变。
2. BLOCK-03：新增 `output\03_noise_bands_1min.csv`（全部 2,186 日 × 240 个 1 分钟标签的 σ/UB/LB，向量化实现并与 `bands_for` 3 日断言一致）。
3. 图 1/2/4 数据 CSV 增加 sigma/UB/LB 列，保证图-数一致。
4. build_nb.py 重建 main.ipynb 后以 run_notebook.py 干净内核完整重跑。

## 验收标准

- 干净内核 EXECUTION OK；图目检 UB/LB 为逐分钟曲线
- 引擎产物不变性：除图与图数据 CSV 外全部产物与 review\run_02\sha_after.json 基线逐字节一致；trade_record.csv 不变；ext 冻结输入未触碰
