# MASFactory 论文复现日志

记录建立日期：2026-10-09。历史内容依据已有核对报告、处理报告和 API 运行记录回填；未保存的执行细节不作补写。本文日期使用北京时间（UTC+8），机器运行记录保留 UTC 时间。

## 1. 目标、范围与当前状态

目标论文：*Beyond Frameworks: Unpacking Collaboration Strategies in Multi-Agent Systems*（ACL 2025）。使用 MASFactory 重建论文的协作流程，并在可取得的数据与模型条件下验证实验结论。

当前范围为 SES 场景下的 evidence-based fact-checking（EBFC），使用 AMBIFC 数据；先完成单 Agent 基线，再进入多 Agent 配置。MIMIC-III / PDDP 暂不开展：尚未申请访问权限，考虑申请所需时间，按与师兄讨论后的安排优先完成另一个数据集。这里应记录“尚未申请/未取得权限”，不能写成“申请被拒绝”。最终提交 README 需要说明范围限制。

| 工作项 | 状态 | 当前证据或限制 |
|---|---|---|
| AMBIFC 数据来源核对 | 已完成本地核对 | 官方来源、字段、作者示例及论文实例相互对应；未获得远端官方文件哈希 |
| 作者预处理流程重建 | 已完成 | 生成 501 条样本，作者 10 条示例全部精确匹配 |
| 与论文完整评测集逐条一致 | 未确认 | 缺少作者完整输入、样本清单或校验和 |
| MASFactory Agent_all 实现 | 已完成初版及离线检查 | 尚无成功的在线推理结果 |
| 原 GPT 快照在线调用 | 被当前令牌权限阻塞 | 服务商返回 HTTP 403 |
| 单 Agent 准确率、token 成本 | 未开展评测 | 不报告数值，不将失败调用计为模型答错 |
| 多 Agent 协作实验 | 未开始 | 等待单 Agent 基线验证 |

## 2. 记录约定

本项目采用三层记录：README 说明当前如何运行；本日志保存过程、决定和复现边界；JSON 产物保存每次运行的具体证据。

- 每次有实质进展时追加条目，包含目的、输入及版本、命令、观察结果、结论、差异与下一步。
- 已有实验记录不覆盖。后续发现早先结论有误时，新增更正条目，并同步更新本文的当前状态。
- 失败运行也保留，区分环境、权限、格式解析和模型判断错误。
- 结论区分“论文明确说明”“作者代码显示”“本地测得”和“当前推断”。单条样本跑通不能代表论文指标复现成功。
- 日志不写 API 密钥、完整环境变量或请求认证头；只记录配置变量名及必要的接口域名。

## 3. 实验环境与版本锚点

2026-10-09 补采的环境信息如下；这是记录建立时的环境快照，不冒充更早运行时已完整冻结的环境。

| 项目 | 本地值 |
|---|---|
| 系统 | Windows 11，10.0.26200 |
| 在线测试 Python | 3.12.4，`D:/Anaconda/python.exe` |
| MASFactory 源码目录 | `D:/Graduate student/MASFactory-main` |
| MASFactory 源码声明版本 / 已安装包版本 | 1.0.4 / 1.0.4；测试实际优先导入本地源码 |
| openai / tiktoken / tenacity | 2.29.0 / 0.13.0 / 8.5.0 |
| 模型请求名 | `gpt-4o-2024-08-06` |
| API 适配器 | MASFactory `LegacyOpenAIModel`，Chat Completions |
| API 域名 | `api.apiyi.com`，第三方服务商 |
| 配置变量 | 当前使用 `OPENAI_API_KEY`、`OPENAI_BASE_URL`；脚本也支持 `OPEN_API_KEY` |
| Git 版本 | 本地 MASFactory 目录无法取得 Git HEAD；不编造提交号 |

关键脚本、MASFactory 调用链文件与原始/处理后数据的 SHA-256 保存在 [environment_20261009.json](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/records/environment_20261009.json>)。这些哈希用于识别当前文件内容，不等于完整依赖锁定，也不能替代官方发布认证。后续代码发生变化，应另存新快照。

## 4. 过程记录

### R001 — 2026-10-08：核对原始数据来源

**目的：** 确认下载到 `original_data/ambifc` 的文件是否属于目标论文使用的 AMBIFC，并判断作者提供的少量示例能否重建。

**依据和操作：** 核对论文 §4.1.1、参考文献、AMBIFC 官方仓库的发布入口及数据字段；解析本地六份 train/dev/test × certain/uncertain JSONL；比较本地 ZIP 与解压文件；使用作者筛选函数重建示例。详见 [AMBIFC 核对报告](<D:/Graduate student/masfactory论文/original_code/dataset_audit/AMBIFC核对报告.md>)。本条沿用该报告的日期；当时完整终端命令未在本日志中保存，不补造执行记录。

**观察：**

- 六份 JSONL 共 90,318 条段落记录；不能把段落数当作独立 claim 数。
- 目标 `test.certain.jsonl` 有 5,121 条段落记录、3,224 个不同 claim_id。
- 六份解压文件与本地 ZIP 中对应内容的哈希一致；这只验证本地解压一致性。
- 作者 10 条示例的 claim、目标标签、证据文本、证据标签及证据顺序全部精确匹配。
- 论文 Appendix D、Table 6（PDF 第 15 页，印刷页 21375）的 Ray Donovan 示例对应 claim_id `7467`，原始文件第 8 行。PDF 有排版差异，不称其文本逐字一致。

**结论：** 本地数据与论文引用的 AMBIFC 来源及公开实例吻合。仍不能确认重建样本与论文完整评测输入逐条一致，也没有官方远端哈希认证。

### R002 — 2026-10-09：重建作者的两阶段预处理

**目的：** 从完整原始文件生成后续实验输入，不把仓库的 10 条示例当作完整评测集。

**输入：** `original_data/ambifc/ambifc_publish-20261008T093810Z-1-001/ambifc_publish/test.certain.jsonl`。完整绝对路径和 SHA-256 见 [preprocessing_report.json](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/data/processed/preprocessing_report.json>)。

**实现：** [prepare_data.py](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/prepare_data.py>) 直接加载作者 `filter_claim_data` 与 `process_filtered_data` 原函数。第一阶段保留句子标注完全一致且具有标签多样性的段落，按 claim_id 保存；第二阶段去空文本、优先排列与目标标签一致的证据，最多保留 6 条。

**可重跑命令**（以下命令以 `D:/Graduate student/masfactory论文/original_code` 为工作目录；这是一条复现入口，不代表更早终端使用了同一 Python 可执行文件）：

```powershell
python -B -X utf8 masfactory_ses/prepare_data.py
```

**本地结果：**

| 指标 | 数值 |
|---|---:|
| 原始段落记录 | 5,121 |
| 通过第一阶段单条筛选的段落 | 539 |
| 同 claim_id 后记录覆盖前记录次数 | 38 |
| 第一阶段 / 最终样本数 | 501 / 501 |
| supporting / refuting 目标标签 | 409 / 92 |
| 作者示例精确匹配 | 10 / 10 |

最终证据组合为“中立 + 支持”407 条、“中立 + 反驳”91 条、仅支持 2 条、仅反驳 1 条。后面三个样本为 `2456`、`8185`、`8365`：第一阶段检查时有带标签的空文本，第二阶段去空后只剩一条证据。忠实保留原行为，未擅自删除。

**核验：** 与前次独立核对的 501 条输出内容和顺序一致；每条结果有原始行号追踪；全部证据非空、每样本 1–6 条。产物见 [处理报告](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/data/processed/preprocessing_report.json>)和[来源追踪](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/data/processed/source_records.json>)。

**决定：** 保留重复 claim_id 覆盖、证据按标签排序、去空后不再检查多样性等作者行为。数据加载额外严格检查 JSONL，遇到损坏记录报错；当前输入全部有效，因此未改变本次样本结果。

### R003 — 2026-10-09：明确文件名与模型版本的证据位置

**核实结果：**

| 问题 | 证据 | 可得结论 |
|---|---|---|
| 使用什么数据集？ | 论文 PDF 第 5 页，§4.1.1 SES 段落 | 使用 AMBIFC |
| 为什么选 `test.certain.jsonl`？ | 作者 `fact_code/filter_claim_data.py:154` 的注释运行示例 | 文件选择来自公开代码；论文未直接写出文件名 |
| 实验读哪个处理文件？ | 作者 `fact_code/G1-P1-I1-C1.py:12` | 读取 `filtered_test_certain_processed.json` |
| 原模型是什么？ | 同页 §4.1 脚注 1；作者 `fact_code/api.py:3` | `ChatGPT-4o-0806` 对应代码请求名 `gpt-4o-2024-08-06` |

**更正：** 不再将“根据作者代码选择的文件”表述为“论文正文指定的文件”。作者预处理主程序第二阶段输出名带 `_new`，实验脚本读取名不带 `_new`；本项目直接调用函数并显式指定不带 `_new` 的输出名。

**模型目录核对：** 当日查看 [OpenAI GPT-4o 官方文档](https://developers.openai.com/api/docs/models/gpt-4o)，Snapshots 中仍列出该快照。该观察不保证第三方服务商或某个令牌有访问权限。

### R004 — 2026-10-09：实现 MASFactory 单 Agent 并完成离线核验

**目的：** 先验证一个样本从处理后数据、MASFactory Agent 到结果解析的链路。

**实现：** [single_agent.py](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/single_agent.py>) 使用 `SingleAgent`、`LegacyOpenAIModel` 和自定义 `PaperFormatter`，以 `Agent_all` 方式将样本全部证据按原顺序用换行连接。模型只接收 claim、证据文本、原作者 instruction、空历史和 Result/Explanation 输出要求。

**配置：** 样本 `7467`，6 条证据；请求精确快照 `gpt-4o-2024-08-06`；不显式设 temperature；输出上限 512 tokens；生成不自动重试，不自动切换模型。脚本每次只处理一条样本。

**离线检查：** 使用本地假模型实际经过 MASFactory 调用路径，验证 system/user 消息逐字一致；用 AST 核对 instruction 和输出要求与作者源码相同；替换 gold label 和证据标签不会改变提示词；非法类别返回被解析器拒绝。检查全部通过。该检查由临时终端脚本执行，未保存为独立测试文件，不把它写成已有持续集成测试。

**已知差异：** 作者未提供独立 Agent_all 基线实现，证据换行连接属于重建选择；本次增加 512-token 输出上限；结果采用标签严格相等，替代作者子串比较；成功后记录 API usage，尚未与论文的纯文本 tiktoken 统计口径对齐。上述差异必须在正式评测前评估并固定。

### R005 — 2026-10-09：原模型 API 连通测试失败

**实际命令**（工作目录同 R002）：

```powershell
python -B -X utf8 masfactory_ses/single_agent.py --claim-id 7467
```

以下三次均针对同一条样本，未批量运行 501 条；未获得成功的模型输出。时间来自运行 JSON 的 UTC 起始时间换算为北京时间。

| 本地起始时间 | 运行条件 | 结果 | 记录 |
|---|---|---|---|
| 21:54:47 | 沙箱内首次尝试 | ProxyError，网络连接受阻 | [135448Z](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/results/smoke_agent_all_7467_20261009T135448752049Z.json>) |
| 21:55:07 | 获准沙箱外重试 | HTTP 403，PermissionDeniedError | [135516Z](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/results/smoke_agent_all_7467_20261009T135516096748Z.json>) |
| 21:56:36 | 增加脱敏错误记录后再次尝试 | HTTP 403，明确为模型权限拒绝 | [135639Z](<D:/Graduate student/masfactory论文/original_code/masfactory_ses/results/smoke_agent_all_7467_20261009T135639792190Z.json>) |

服务商原始错误的关键内容：`该令牌无权使用模型：gpt-4o-2024-08-06`。

**结论：** 当前请求到达服务商并被令牌权限拒绝；不能据此判断官方模型下线、所有服务商均不可用，或模型在该样本上预测错误。没有返回模型名、判断结果及 API usage，因此准确率、成功推理 token 用量与费用均不作数值结论。

**处理决定：** 保留精确模型版本与全部失败记录，停止重复尝试。下一步检查服务商的令牌允许模型及所属分组，确认能否开放该快照；不擅自换成 `gpt-4o` 别名或其他模型后宣称复现原版本。

### R006 — 2026-10-09：建立本地 Git 版本管理

**目的：** 在复现日志之外保存代码与实验产物的可追溯版本。

**范围：** 以 `masfactory_ses` 为独立仓库根目录，使用 `main` 分支。将当前代码、文档、处理后数据、环境快照和脱敏的失败运行 JSON 纳入首个版本；保留已有空白 `test.py`。原论文、作者代码、原始下载和 MASFactory 源码保持在仓库外，现有路径依赖未改变。

**检查与决定：** 入库前检查现有 13 个文件（约 1.70 MB），未发现所检查模式的疑似密钥或私钥；该检查不是完整的安全审计。增加 `.gitignore` 排除密钥文件、原始下载、虚拟环境及缓存；增加 `.gitattributes` 保留原始字节，避免 Git 换行转换使已有 SHA-256 失效。使用已有 Git 用户配置创建首个本地提交，不设置远程地址、不发布代码。

**版本查询：** 当前版本使用 `git log -1 --oneline` 查询，后续实验在记录中写入当时的提交号。首个提交号不写入其自身文件，避免自引用；此前环境快照中的 MASFactory Git 状态仍是当时事实，本次未给外部 MASFactory 目录初始化 Git。

### R007 — 2026-10-09：配置 GitHub、起草数据确认邮件并复核模型状态

**远程仓库：** 用户指定 `https://github.com/lxyaa1/reproduce.git`；原消息链接尾部的逗号按标点处理。已配置为 `origin`，采用普通推送，不强制覆盖远程历史。首次远程查询受沙箱网络限制；沙箱外直连两次发生连接重置。检查发现系统已启用 `127.0.0.1:7890` 代理，使用 Git 单次 `-c http.proxy=...` 参数后查询成功，远程没有已有 refs。代理参数仅作用于本次命令，不更改全局 Git 配置。推送结果待确认。

**作者询问：** 邮件草稿保存在 `docs/author_data_inquiry.md`，收件地址 `hcwang@ir.hit.edu.cn` 来自作者仓库 README。询问 AMBIFC 具体文件及发布版本、501 条是否对应完整评测集、是否额外筛选、各基线与协作配置是否共用样本，以及能否提供最终文件或 claim ID。邮件尚未发送。

**模型复核：** 当日重新读取 [官方 GPT-4o 模型页](https://developers.openai.com/api/docs/models/gpt-4o)和[停用公告](https://developers.openai.com/api/docs/deprecations)。模型页仍列出 `gpt-4o-2024-08-06`；停用公告未找到该精确版本的下线条目。结合已保存的第三方 API 403，可确认当前服务商令牌无法访问该版本；仅凭错误无法进一步区分令牌白名单、账户分组或服务商未提供该快照。没有证据将该失败归因于 OpenAI 已停用原快照，也未用官方账户另做成功调用验证。

## 5. 下一步与完成标准

1. **恢复模型权限。** 在服务商侧确认令牌可访问精确快照。完成标准为重新运行一条样本并取得真实模型响应；如仍无权限，记录限制，另行确定是否开展替代模型实验。
2. **验证单条 Agent_all。** 检查真实发送消息、解析输出、返回模型名、finish_reason 和 usage；确认未截断且未传入人工答案。一次成功只证明链路可用。
3. **固定评测方案。** 确定样本范围、Agent_all 与论文其他单 Agent 基线的对应、token 统计口径、输出上限、重复运行安排及错误处理。明确“501 条公开代码重建集”这一边界；不能将失败样本静默删去。
4. **完成单 Agent 评测后再扩展协作。** 保存逐样本预测、标准答案、错误状态、token 和汇总统计，再进入论文多 Agent 配置。当前尚未启动完整评测。
5. **交付时同步限制说明。** 包括 MIMIC 未取得权限、完整原评测样本未知、基线重建选择、模型访问条件及仍存在的统计口径差异。

## 6. 后续追加模板

```text
### R008 — YYYY-MM-DD：本次工作名称

目的：
输入/样本范围：
代码与环境版本：Git 提交号；无 Git 时记录快照/文件哈希
模型/API/参数：仅写必要信息，不写密钥
工作目录与命令：
实际观察：样本数、成功/失败数、指标、错误等
产物与日志路径：
结论：哪些被验证、哪些仍未确认
与论文或上次运行的差异：
决定及下一步：
```
