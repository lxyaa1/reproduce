# 使用 MASFactory 复现 SES / EBFC

当前阶段：已重建论文公开代码对应的输入数据，并实现 MASFactory 单 Agent 冒烟测试。2026-10-09 实测原模型 `gpt-4o-2024-08-06` 时，服务商返回 HTTP 403：当前令牌无权使用该模型；尚未获得真实推理结果，也未开展批量评测。

过程记录见 [复现日志 REPRODUCTION_LOG.md](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/REPRODUCTION_LOG.md>)：包含数据来源证据、历次处理与测试结果、复现差异、环境快照和后续记录模板。本 README 维护当前运行方法，历史尝试与决定追加到复现日志。

## 版本管理

`masfactory_ses` 作为独立本地 Git 仓库管理，主分支为 `main`。代码、文档、当前处理后数据、环境记录和脱敏运行结果一并纳入版本；原始下载、密钥文件、虚拟环境及缓存由 `.gitignore` 排除。`.gitattributes` 禁止自动换行转换，以保留数据和代码哈希对应的原始字节。

原论文 PDF、作者代码、AMBIFC 原始数据和 MASFactory 源码仍位于仓库外，未复制入库。复现脚本目前依赖前述本地目录布局；只克隆本仓库并不足以重建完整运行环境。远程 `origin` 已配置为 [lxyaa1/reproduce](https://github.com/lxyaa1/reproduce)，推送进展记录在复现日志中。

## 数据来源和复现边界

- 目标论文：Beyond Frameworks: Unpacking Collaboration Strategies in Multi-Agent Systems，ACL 2025。
- 原始数据：AMBIFC 发布包中的 `test.certain.jsonl`。
- 处理实现：直接调用相邻 `collaboration_MAS-main/fact_code/filter_claim_data.py` 的原始函数，不修改作者筛选逻辑。
- 作者仓库的 `data_example.json` 只有 10 条，用于示例比对，不作为完整评测集。
- 该流程重建的是“公开代码处理本地原始数据得到的实验输入”。作者未公开完整实验样本清单，不能宣称与论文表格使用的全部样本逐条相同，也不能将本地统计的样本数视为论文明确报告的样本数。
- 本项目当前仅开展 SES / EBFC；MIMIC-III 权限未申请，PDDP 暂不纳入范围。

### 论文与文件名的证据边界

- 论文 PDF 第 5 页（印刷页码 21365），§4.1.1 的 “Structured Evidence Synthesis (SES)” 段明确写明 EBFC 使用 AMBIFC（Glockner et al., 2024）。全文未出现 `test.certain.jsonl`，不能称论文正文指定了这个文件。
- `../collaboration_MAS-main/fact_code/filter_claim_data.py:154` 的第一阶段示例（注释代码）指定 `../../data/AmbiFC/test.certain.jsonl`，第 155 行输出 `filtered_test_certain.json`。这是选择该原始文件的直接代码依据。
- 同文件第 166–167 行的第二阶段读取 `filtered_test_certain.json`，输出名带 `_processed_new.json`；实际实验脚本 `G1-P1-I1-C1.py:12` 读取不带 `_new` 的 `filtered_test_certain_processed.json`。本项目调用原函数、显式指定后者为输出名；不把这处命名差异隐去。
- 同页 §4.1 说明所有实验使用 ChatGPT-4o，脚注 1 为 “ChatGPT-4o-0806 version”；`fact_code/api.py:3` 将模型名具体写为 `gpt-4o-2024-08-06`。
- 2026-10-09 查阅 [OpenAI GPT-4o 模型文档](https://developers.openai.com/api/docs/models/gpt-4o)，其 Snapshots 列表仍包含该版本。官方模型目录与第三方服务商当前令牌的访问权限是两件事。

## 运行预处理

本步骤只需要 Python 标准库，不需要安装 MASFactory、配置模型密钥或调用 API。

在当前 `masfactory_ses` 目录执行：

```powershell
python -B prepare_data.py
```

脚本根据自身位置定位作者代码，默认在相邻 `original_data/ambifc` 下查找唯一的 `test.certain.jsonl`，不依赖终端的工作目录。也可以提供明确路径：

```powershell
python -B prepare_data.py --input "你的路径/test.certain.jsonl"
```

每次运行重新生成本项目的处理结果，不修改原始数据和作者代码。JSONL 格式损坏会明确报错；作者原读取函数会打印错误并跳过，我们在读取层选择报错，以防悄悄缺失样本。当前文件全部有效，因此这一区别不改变本次结果。

## 两阶段处理

1. `filter_claim_data`：只保留标注完全一致的句子；若剩余标签只有一种，排除该段落；结果按 `claim_id` 保存。
2. `process_filtered_data`：去除空字符串；把与目标标签相同的证据排在前面；最多保留 6 条，其余位置用不同标签的证据按原顺序补足。

为忠实于作者代码，保留如下行为：

- 多个符合条件的段落共享 `claim_id` 时，后出现的覆盖先出现的，不进行段落合并。
- 第一阶段的标签多样性检查包含空字符串的标注；第二阶段删除空字符串后不再检查多样性。
- 即使不足 6 条，也先排列与目标标签一致的证据。
- 证据筛选使用已有人工标签；后续 Agent 提示词只应接收陈述和证据文本，标准答案用于离线评估。

## 输出文件

全部输出到 `data/processed/`：

| 文件 | 用途 |
|---|---|
| `filtered_test_certain.json` | 第一阶段结果 |
| `filtered_test_certain_processed.json` | 后续单 Agent / 多 Agent 的完整输入 |
| `preprocessing_report.json` | 处理数量、标签分布、示例比对、来源及输出 SHA-256 |
| `source_records.json` | 每条结果来自原始文件的哪一行、哪个段落；以及覆盖事件 |

校验包含：作者 10 条示例的完整对象比较；最终证据非空且不超过 6 条；如已有前次核对结果，还比较所有样本内容及排列顺序。

## 本地重建结果

2026-10-09：原始输入 5,121 条段落记录，其中 539 条通过第一阶段单条筛选；发生 38 次同 claim_id 覆盖，剩余 501 个 claim_id。第二阶段输出仍为 501 条样本；目标标签 supporting 409 条、refuting 92 条。

最终证据组合：407 条“中立 + 支持”、91 条“中立 + 反驳”、2 条仅支持、1 条仅反驳。三个单一标签样本 `2456`、`8185`、`8365` 均只剩一条非空证据，保留用于忠实复现。

本次作者 10 条示例全部精确匹配；与前次独立核对保存的 501 条结果内容和顺序完全一致，501 条结果均有原始行号记录。若切换原始数据或作者代码版本，以新报告为准，并重新确认复现范围。

## MASFactory 单 Agent 冒烟测试

`single_agent.py` 使用 `SingleAgent` 和 `LegacyOpenAIModel`（Chat Completions，与原作者接口一致）。默认优先导入 `D:/Graduate student/MASFactory-main` 下的本地库；可用 `MASFACTORY_SOURCE` 指定另一份源码路径，否则使用已安装库。

在当前目录执行（每次只调用一个样本）：

```powershell
python -B -X utf8 single_agent.py --claim-id 7467
```

只查看提示词、不调用 API：

```powershell
python -B -X utf8 single_agent.py --claim-id 7467 --dry-run
```

密钥依次读取 `OPEN_API_KEY`、`OPENAI_API_KEY`，地址读取 `OPENAI_BASE_URL`；本次实际存在的是 `OPENAI_API_KEY`。不将密钥写入报告。返回结果或脱敏错误保存于 `results/` 中带时间戳的 JSON 文件。

复现设计与限制：

- 实现 `Agent_all`：将一条样本全部证据文本按原顺序用换行连接，传给一个 Agent。作者未提供独立的单 Agent 基线脚本，因此这个连接方式属于本项目重建选择。
- 原样保留作者 `G1-P1-I1-C1.py:48–52` 的 instruction、Python 字典字符串提示结构、空历史以及 Result/Explanation 输出要求。标准答案和证据人工标签不进入模型。
- 不显式设 temperature，与作者 API 帮助函数一致。为限制本次冒烟测试开销设置 `max_tokens=512`，这是相对原代码的显式差异。
- 严格解析三类标签，用标签完全相等评估，避免作者子串比较带来的误判。
- 单次生成不自动重试、不更换模型、不自动运行全部 501 条。MASFactory 适配器初始化还会查询模型元数据，该查询不是推理请求。
- 成功时保存接口返回的模型名、原始回答及 API token usage；它们与论文按提示文本计算的 token 口径并不完全相同。第三方接口返回的模型名不能独立证明其上游模型身份。

离线检查已通过：实际经过 MASFactory 的消息与预期 system/user 消息逐字一致；两个提示常量与作者源码 AST 比对一致；修改 gold label 和所有证据标签不会改变提示词；无效结果标签会被拒绝。

2026-10-09 联网结果：沙箱内首次遇到 ProxyError；获准沙箱外运行后，服务商 `api.apiyi.com` 返回 HTTP 403、`PermissionDeniedError`。再次记录具体原因得到：`该令牌无权使用模型：gpt-4o-2024-08-06`。详见 `results/smoke_agent_all_7467_20261009T135639792190Z.json`。这证明当前令牌不能调用该模型，不证明模型已下线。需要在服务商侧检查令牌的允许模型/所属分组，获得该快照的权限后重跑；目前不能报告样本准确率或成功调用的 token 用量。
