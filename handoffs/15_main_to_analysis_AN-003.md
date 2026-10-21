# 代理任务单 / 回报

## 元信息

- run_id：RUN-001
- task_id：AN-003
- stage：result_analysis（修订轮）
- from：main
- to：analysis（本会话无子代理，由 main 亲自执行该角色）
- cycle：2
- status：IN_PROGRESS

## 权限

- 只读：output\、review\cycle_02.md、pdf_text.txt、handoffs\12、handoffs\14
- 可写：reports\（三报告更新）、handoffs\16_analysis_to_main_AN-003.md
- 禁止：plan.md、process_log.jsonl、data\processed、main.ipynb、build_nb.py

## 任务

以 CR-002 PASS 后的修订结果更新交付报告：
1. reproduction-report.md：假设清单补 H13（VWAP 网格口径）/H14（午休轴）/H15（输出布局）；核心结果表与交易级数值替换为修订后版本；验证证据补 cycle_02；产物清单改 grids 布局；加修订记录段。
2. comparison-report.md：T01-T33 中受 VWAP 修订影响的行全部更新（T07/T09/T11/T12/T13/T14/T15/T16/T17/T18/T21/T22/T23/T24/T30/T31/T33 数值；判定维持）；§4 成本机制锚点改 1.395；§5 主结论同步；加修订记录段。
3. process-report.md：补修订轮（Q-002 → CD-002 → CR-002 → AN-003）与自检 bug 闭环记录。
4. 验收标准：报告内每个数值与 output\ 当前产物一致；论文锚点仍出自 pdf_text.txt；判定汇总计数自洽。

## 回报

（待 analysis 角色填写）
