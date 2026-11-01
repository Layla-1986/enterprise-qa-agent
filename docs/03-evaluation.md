# 评估与限制

实际记录（每个 JSON 包含输入对应的动作、参数、结果和决策依据；输入见文件名及下表）：

| 场景/输入 | 预期 | 实际记录 |
|---|---|---|
| 产品怎么登录 | 有引用回答 | ../examples/live_answer.json |
| 报销期限多久 | 两份冲突，不擅选 | ../examples/live_conflict.json |
| 年假有多少天 | 资料不足 | ../examples/live_missing.json |
| 费用发生后几天内可以报账 | 改写识别冲突 | ../examples/live_rephrase.json |
| 历史为询问报销制度，追问那期限是多久 | 联系上下文并指出冲突 | ../examples/live_followup.json |
| 注入检索工具故障 | 说明失败及缺口 | ../examples/live_failure.json |
| 注入原文读取故障 | 说明失败及缺口 | ../examples/live_read_failure.json |
| 更换为单份 45 天制度 | 引用变更后的内容 | ../examples/live_changed.json |

本次真实模型为 deepseek-chat；每项一次，非统计评估。冲突路径为 search → read → read → finish；故障路径为 search → search → finish，展示了模型根据不同结果选择动作。离线单元测试结果见 ../examples/test_results.txt（10 项通过），覆盖变更、缺失、故障、步数上限伪造引用、跳过检索读取和重复引用冒充冲突。真实模型对恶意文档及大规模数据未测试。字符匹配可能漏掉冲突；引用校验不证明答案语义正确。

完整输入和追问历史见 ../examples/inputs.json；`python -X utf8 examples/check_records.py` 检查状态、原文逐字引用和故障记录，不能替代语义判断。`python -X utf8 examples/run_live.py` 可使用当前配置重新运行，会覆盖现有记录且可能产生费用；模型输出非确定性。运行环境为 Windows、Python 3.11.3、deepseek-chat，数据与代码在本项目内。

本轮重跑上下文追问时，模型曾返回无法解析的 JSON，程序返回 model_error；该失败保留在 ../examples/live_followup_parse_failure.json。随后相同输入再运行一次得到 conflict，保存在 ../examples/live_followup.json。模型输出并非稳定，当前没有自动修复格式的重试机制。新增测试覆盖检索结果静默截断、未读取全部命中即回答、检索失败后仍回答。

## 检索对照与澄清改进

运行 `python -X utf8 examples/eval_retrieval.py` 可复现 [检索结果](../examples/retrieval_results.json)。`data/retrieval_eval.json` 包含 9 条手工构造的查询，其中 7 条有相关文档、2 条为资料外问题；相关片段由本项目作者按这 3 个合成文档人工标注。基线是未做同义词归一化的字符二元组检索，当前方案增加了少量人工同义词归一化；两者均返回所有有重叠的片段。

| 指标 | 基线 | 当前 |
|---|---:|---:|
| 正样本宏平均召回率 | 85.7% | 100% |
| 资料外查询误召回率 | 50% | 50% |

“报账”命中依赖已配置的“报账→报销”规则。这些样本规模很小，且同义词与开发规则并非独立设计，不能作为泛化性能或生产准确率；误召回也说明需要后续改进。召回统计未评估排序、语义支持或最终问答成功率。

最初对无上下文的“期限是多久？”模型从检索结果中猜测了报销主题，记录在 [模糊问题失败](../examples/live_ambiguous_failure.json)。随后增加通用澄清指令，对另一句“需要多长时间？”单次运行返回 clarification，请用户说明事项，见 [澄清记录](../examples/live_clarification.json)。这是提示层改进，模型仍可能误判，不能保证所有模糊问题都会触发澄清。更改提示后，另行运行 [明确回答](../examples/current_answer.json)、[冲突](../examples/current_conflict.json) 和 [检索失败](../examples/current_failure.json)；原 `live_*.json` 中其他用例是此前版本的运行记录，并非本轮全部重跑。
