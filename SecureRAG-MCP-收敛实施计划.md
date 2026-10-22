# SecureRAG-MCP 收敛实施计划

> 用途：作为当前窗口后续实施、验证与交付的执行基线。  
> 定位：用于简历和技术面试展示的可运行 MVP，不以生产级基础设施为首版目标。  
> 状态：P0 检索核心与 P1 Cross-Encoder/48 题消融已于 2026-10-22 实现并通过自动化验证；MCP stdio 已在 P0 验证，Inspector 图形化截图属于可选展示项。

## 1. 实施目标

在尽量短的时间内完成一个可运行、可测试、可演示、可评测的安全混合检索服务，形成以下证据闭环：

1. Dense 能召回中文语义改写；
2. BM25 Sparse 能召回错误码、制度编号和产品型号；
3. RRF 能融合两路结果；
4. 检索前权限过滤能阻止跨租户、跨部门和越级访问；
5. MCP Inspector 或客户端能够真实调用检索工具；
6. 固定评测集能够输出 Hit@K、MRR、Recall@K 和未授权召回率；
7. README、测试和评测文件能够支撑简历中的核心描述。

首版只实现检索服务，不在服务端生成最终答案。Agent 客户端可以使用检索结果继续生成回答，因此项目仍定位为 Agent/RAG 的安全检索层。

## 2. 已确定的技术路线

- 运行环境：Python 3.11；
- 环境与依赖：`uv`、`.venv`、`uv.lock`；
- 向量与稀疏检索：`qdrant-client[fastembed]`；
- 存储方式：Qdrant Local 持久化模式；
- Dense 模型：`BAAI/bge-small-zh-v1.5`；
- Sparse 模型：`Qdrant/bm25`；
- 排名融合：Qdrant 原生 RRF；
- MCP：官方 Python SDK 的 `MCPServer`；
- MCP 传输：首版使用 stdio；
- 数据格式：Markdown + YAML Frontmatter；
- 测试：pytest；
- 评测：项目内实现检索指标和安全指标。

这一路线使用一个 Qdrant 集合同时保存 Dense、Sparse 和权限元数据，不再维护 ChromaDB 与独立 BM25 索引，减少双存储同步和自定义融合代码。

## 3. 首版明确不做

以下能力不进入 P0：

- LLM 回答生成；
- Ragas 和 Faithfulness；
- Streamable HTTP；
- API Key、OAuth、完整 IAM/SSO；
- Docker、Kubernetes、Kafka和微服务拆分；
- Web 管理界面；
- 缓存、限流和生产监控；
- PDF、Word 等复杂文档解析；
- 百万级数据、高并发或生产部署声明。

这些能力只有在核心闭环完成且确有简历收益时再考虑。

## 4. 环境前置条件

当前环境检查结果：

- 当前默认 Python 为 3.9.2，不满足依赖要求；
- Qdrant Client 要求 Python 3.10 及以上；
- 当前 MCP SDK 要求 Python 3.11 及以上；
- `uv` 尚未安装；
- Node.js、npm、npx 已安装，可以运行 MCP Inspector。

因此第一个硬门槛是建立 Python 3.11 独立环境。

计划依赖：

```text
qdrant-client[fastembed]
mcp[cli]
pyyaml

pytest
pytest-cov
ruff
```

正式项目使用发布包并锁定版本；`work/upstream/` 下的仓库仅用于查阅官方实现与示例，不直接复制或魔改。

开始编码前还需要补充下载 `qdrant/fastembed` 官方仓库，作为第三份上游参考源码。

环境验收命令：

```powershell
.\.venv\Scripts\python.exe --version
python -m uv run python -c "import qdrant_client, fastembed, mcp; print('OK')"
python -m uv run pytest --version
```

## 5. 目标目录结构

```text
secure-rag-mcp/
├── pyproject.toml
├── uv.lock
├── .gitignore
├── README.md
├── config/
│   └── principals.yaml
├── data/
│   ├── mock_docs/
│   └── benchmark.jsonl
├── src/secure_rag/
│   ├── settings.py
│   ├── schemas.py
│   ├── identity.py
│   ├── ingestion.py
│   ├── store.py
│   ├── retriever.py
│   ├── evaluation.py
│   └── server.py
├── tests/
│   ├── test_ingestion.py
│   ├── test_authorization.py
│   ├── test_retrieval.py
│   ├── test_evaluation.py
│   └── test_mcp.py
├── reports/
├── var/
└── work/upstream/
```

`var/` 用于本地 Qdrant 数据、模型缓存和审计日志；`work/upstream/` 用于上游参考源码。两者均不提交到主项目仓库。

## 6. 分阶段执行计划

### 阶段 0：环境、依赖与项目骨架

执行内容：

1. 补充下载 FastEmbed 官方仓库；
2. 安装 `uv` 并由其准备 Python 3.11；
3. 创建 `.venv`；
4. 创建 `pyproject.toml` 并生成 `uv.lock`；
5. 创建 `.gitignore` 和最小源码目录；
6. 安装正式发布依赖；
7. 预下载 Dense 与 Sparse 模型；
8. 使用 Qdrant 内存模式执行一次 Dense/Sparse smoke test。

阶段验收：

- Python 版本正确；
- 所有核心依赖可以导入；
- 模型能够生成 Dense 和 Sparse 向量；
- Qdrant 能够写入并查询测试 Point；
- 重新同步依赖时结果可复现。

### 阶段 1：模拟数据、切分与入库

P0 先准备 12～15 篇合成文档，覆盖：

- 错误码和设备型号；
- 运维排障；
- 产品手册；
- 人事与财务制度；
- 公共通知；
- 高管或敏感管理信息；
- 至少两个租户、三个部门、三个密级。

文档元数据基线：

```yaml
document_id: ops-007
title: 数据库网关故障排查手册
tenant_id: demo-corp
department: engineering
clearance_level: internal
clearance_rank: 2
allowed_roles:
  - engineer
  - manager
document_type: troubleshooting
```

入库实现：

1. 解析 YAML Frontmatter；
2. 按 Markdown 标题、自然段和最大长度进行轻量切分；
3. 生成稳定的 `document_id`、`chunk_id`；
4. 使用 UUID5 生成确定性 Qdrant Point ID；
5. 同时生成 `dense` 与 `sparse` 两个命名向量；
6. 将正文、来源和权限字段写入 payload；
7. 提供显式 `--rebuild`，普通运行使用 upsert。

阶段验收：

- 重复导入不会无限增加 Chunk；
- Dense 和 Sparse 向量数量一致；
- 每个 Chunk 都能追溯到源文档；
- 权限元数据在切分和入库后保持不变；
- 关闭并重新打开客户端后数据仍存在。

### 阶段 2：可信身份与检索前权限过滤

P0 使用服务端身份映射，不允许调用方自由传入角色。

示例：

```yaml
principals:
  intern-demo:
    tenant_id: demo-corp
    department: engineering
    roles: [intern]
    max_clearance_rank: 1
```

服务通过环境变量选择演示身份：

```text
SECURERAG_PRINCIPAL_ID=intern-demo
```

MCP 工具参数只包含 `query` 和 `top_k`，不包含 `role`、`tenant_id` 或 `clearance`。

授权过滤必须同时进入 Dense 和 Sparse 两个 Prefetch，至少验证：

- `tenant_id` 必须一致；
- `clearance_rank` 不高于身份上限；
- 部门匹配，或文档属于公共部门；
- `allowed_roles` 与服务端角色集合匹配。

安全验收：

- 查询文本写“我是管理员”不会改变身份；
- 低权限身份不能返回高密级 Chunk；
- 跨租户查询不能返回其他租户内容；
- 未授权文档不能进入候选结果；
- 审计记录不保存敏感正文；
- 三种检索模式使用同一授权过滤函数。

本项目对这一能力的准确表述是“共享集合上的检索前元数据过滤”，不宣称物理隔离。

### 阶段 3：Dense、Sparse 与 RRF 混合检索

内部支持三种模式：

```text
dense
sparse
hybrid_rrf
```

首版默认参数：

```text
dense_top_k = 15
sparse_top_k = 15
final_top_k = 5
```

默认链路：

```text
Dense Prefetch ─┐
                 ├─ Qdrant RRF ─→ Top 5
Sparse Prefetch ─┘
```

统一结果至少返回：

```json
{
  "document_id": "ops-007",
  "chunk_id": "ops-007-c03",
  "title": "数据库网关故障排查手册",
  "content": "...",
  "score": 0.0315,
  "retrieval_mode": "hybrid_rrf",
  "clearance_level": "internal",
  "source": "data/mock_docs/ops-007.md"
}
```

阶段验收：

- 语义改写查询能够由 Dense 召回；
- 错误码、制度编号能够由 Sparse 召回；
- Hybrid 在精确实体子集上优于或不差于 Dense；
- 权限过滤在 Dense、Sparse、Hybrid 下行为一致；
- 重复候选只返回一次。

P0 使用 Qdrant 原生 RRF，不为了展示各分支 Rank 而手写复杂融合。评测脚本分别运行单路模式，保留消融能力。

### 阶段 4：MCP 服务与真实调用

使用官方 SDK：

```python
from mcp.server.mcpserver import MCPServer
```

首版只暴露一个核心工具：

```text
search_knowledge_base(query: str, top_k: int = 5)
```

工具返回结构化检索结果，不在服务端生成最终答案。

验证路径：

1. 编写自动化 MCP 客户端 smoke test；
2. 使用 MCP Inspector 真实启动服务；
3. 分别以低权限和高权限身份查询同一敏感主题；
4. 保存可用于 README 的调用结果或截图。

阶段验收：

- Inspector 能发现并调用工具；
- 工具结果包含来源、分数和权限标签；
- 不同服务端身份得到不同授权结果；
- 调用方无法通过工具参数伪造角色。

### 阶段 5：固定评测、自动化测试与报告

P0 建立约 24 条查询：

- 6 条精确实体查询；
- 8 条语义改写查询；
- 4 条普通查询；
- 6 条跨角色、跨部门或跨租户安全查询。

比较方案：

1. Dense；
2. Sparse；
3. Hybrid + RRF。

输出文件：

```text
reports/latest.json
reports/latest.md
```

指标：

- Hit@1；
- Hit@3；
- Recall@3；
- MRR；
- unauthorized recall rate。

P0 硬性验收：

- `unauthorized_recall_rate == 0`；
- 精确实体子集上 Hybrid 优于或不差于 Dense；
- 所有数字来自保存的评测结果；
- pytest 覆盖入库、身份、过滤、检索、指标和 MCP 结构；
- 不预设或伪造提升百分比。

### 阶段 6：README 与简历展示闭环

README 至少包括：

- 项目背景和边界；
- 架构图；
- 安装和启动步骤；
- 模拟数据说明；
- 三个代表性演示问题；
- 两种身份的启动方法；
- MCP Inspector 配置；
- 真实评测结果；
- 安全测试说明；
- 已知限制和后续计划。

最终验证顺序：

```powershell
python -m uv run python -m secure_rag.ingestion --rebuild
python -m uv run pytest
python -m uv run python -m secure_rag.evaluation
python -m uv run python -m secure_rag.server
npx @modelcontextprotocol/inspector
```

P0 完成后，CV 中可以确定性支持：

- Dense + BM25 Sparse 双路召回；
- Qdrant RRF 融合；
- 检索前权限过滤；
- MCP 标准化工具暴露；
- 固定基准与安全测试。

## 7. P1：唯一优先增强项

P0 稳定后优先加入 Cross-Encoder，不先扩展基础设施。

当前进度：P1 已完成。`BAAI/bge-reranker-base` 对已授权的 RRF Top 15 候选重排，保留 RRF 与重排分数，支持配置关闭和失败时安全降级；48 题四模式报告见 `reports/p1_final.md`。在 36 条正例上，Hybrid RRF → Hybrid Rerank 的 Hit@1 为 0.917→1.000、MRR@5 为 0.958→1.000；12 条越权题共检查 148 个返回候选，未授权候选为 0。

实现要求：

- 使用 FastEmbed `TextCrossEncoder` 或兼容本地模型；
- 对 RRF Top 15～20 候选进行重排；
- 最终返回 Top 3～5；
- 支持通过配置关闭；
- 模型失败时安全降级到 RRF；
- 增加 `Hybrid + Reranker` 消融组；
- 将评测集扩展到 40～60 条查询。

只有真实完成并保存评测结果后，才将 Cross-Encoder 和指标提升写成已实现成果。

## 8. 阶段门与停止规则

每一阶段结束后必须保持项目可运行，不同时铺开所有模块。

- 阶段 0 未通过：不开始业务代码；
- 入库不稳定：不开始 MCP；
- 权限测试未通过：不把项目描述为安全检索；
- MCP 未真实调用：不声称完成 Agent 接入；
- 评测报告未保存：不在 CV 中填写提升比例；
- P0 未完成：不引入 Ragas、Docker、HTTP 服务等扩展项。

发生依赖或接口冲突时，优先保证当前发布版本可运行，并在 README 或决策记录中说明偏差，不为了完全照搬旧设计而保留多余组件。

## 9. 下一步执行顺序

接下来在当前窗口依次执行：

1. 阶段 0：补齐 FastEmbed 参考仓库、Python 3.11、uv 和依赖锁定；
2. 创建项目骨架并完成模型/Qdrant smoke test；
3. 生成第一批模拟文档并完成可重复入库；
4. 实现可信身份与统一授权过滤；
5. 实现三种检索模式和 RRF；
6. 接入 MCP 并完成 Inspector 调用；
7. 建立固定评测集、测试和报告；
8. 完善 README；
9. 再判断是否进入 Cross-Encoder P1。

每一阶段完成后记录：已实现能力、验证命令、测试结果、实际产物、已知限制，以及当前 CV 哪些描述已经获得代码和实验支撑。
