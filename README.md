# 企业知识问答 Agent（第 3 题）

Python 3.11+，无第三方依赖。文档为合成数据。提供 CLI、本地检索和原文读取；模型以 JSON 动作驱动工具循环。离线 Mock 是规则模拟器，仅用于验证程序链路，不代表真实模型决策能力。

## 运行

在本目录打开 PowerShell：

```powershell
python -X utf8 src/main.py "报销期限多久？" --mock
python -X utf8 -m unittest discover -s tests -v
python -X utf8 examples/eval_retrieval.py
```

真实模型入口需要兼容 OpenAI Chat Completions 的服务。以 PowerShell 环境变量配置（不要将密钥写进仓库）：

```powershell
$env:OPENAI_API_KEY = "你的密钥"
$env:OPENAI_BASE_URL = "你的服务地址/v1"
$env:OPENAI_MODEL = "模型名称"
python -X utf8 src/main.py "报销期限多久？"
python -X utf8 src/main.py "那期限是多久？" --history '[{"role":"user","content":"我想了解员工报销制度"}]'
python -X utf8 src/main.py "报销期限多久？" --fail search
```

也可通过 `--data data/changed_documents.json` 换数据，`--max-steps 12` 控制上限。`.env.example` 为变量说明，本程序读取进程环境变量，不自动加载 .env。

输出为 JSON，包含 status、answer、citations（文档 ID、版本日期、片段 ID、原文）、gaps 和 trace。状态包括 answered、conflict、insufficient、clarification、incomplete、model_error。Trace 保留每一步动作、参数、理由及工具返回；不记录模型内部思维。

## 评审入口

- [需求](docs/01-requirements.md)、[设计](docs/02-solution.md)、[评估](docs/03-evaluation.md)、[AI 使用](docs/04-ai-usage.md)、[复盘](docs/05-retrospective.md)。
- [真实模型冲突](examples/live_conflict.json)、[正常回答](examples/live_answer.json)、[资料不足](examples/live_missing.json)、[检索故障](examples/live_failure.json)、[读取故障](examples/live_read_failure.json)、[改写](examples/live_rephrase.json)、[上下文追问](examples/live_followup.json)、[追问格式失败记录](examples/live_followup_parse_failure.json)、[替换资料](examples/live_changed.json)、[完整输入](examples/inputs.json)、[测试结果](examples/test_results.txt)。
- 运行 `python -X utf8 examples/check_records.py` 校验保存的结果；`python -X utf8 examples/run_live.py` 可重跑真实模型并覆盖记录。
- [澄清前失败](examples/live_ambiguous_failure.json)、[澄清后示例](examples/live_clarification.json)、[检索对照](examples/retrieval_results.json)：小规模合成样本，结果不代表泛化表现。
- 真实模型运行基于环境中配置的 `deepseek-chat` 和兼容接口；模型和服务行为可能随配置或时间改变。结果为单次样例，不代表稳定成功率。
