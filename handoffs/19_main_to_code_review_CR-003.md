# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：CR-003
- stage：code_review（修订轮二）
- from：main
- to：code_review
- cycle：3
- status：IN_PROGRESS

## 任务单

对 CD-003（DEC-012 噪声带 1 分钟全分辨率）做聚焦复审，输出 review\cycle_03.md：

1. **独立复算探针**（第三代码路径，直读 data\processed 分钟 parquet + 日线 csv，不复用 notebook 函数）：
   - 前 14 个样本日 σ/UB/LB 全 NaN（无带不交易）
   - 随机 ≥20 个 (d,τ) 逐值复算 move/σ/UB/LB（mean 仅含 t−14..t−1，反未来函数由构造保证），与 `03_noise_bands_1min.csv` 核对（容差 1e-6，CSV 六位小数截断）
   - 1 分钟分辨率验证：抽样日相邻分钟 UB 变动占比与唯一值计数（证明非检查点步进）
   - 检查点值 = 引擎决策值：1min CSV 与 `03_noise_bands_sample.csv` 全行对齐（含 13:00→11:30 映射）
   - 图 1/2/4 数据 CSV 与 1min 带逐值一致
2. **引擎产物不变性**：以 review\run_02\sha_after.json 为基线，除 7 个有意变更 + 1 个新增外全部一致；trade_record.csv 不变；ext 冻结输入 mtime 核验。
3. **图目检**：UB/LB 逐分钟曲线、午休轴保持、VWAP 步进线语义不变。

## 验收标准

- cycle_03.md 结论 PASS/FAIL 明确，探针脚本留存 review\probe_noise_band_1m.py
