# SecureRAG-MCP

面向简历与技术面试演示的本地安全混合检索服务。项目使用 Qdrant Local 在同一集合中保存 Dense、BM25 Sparse 和权限元数据，通过检索前过滤限制候选范围，并使用官方 MCP Python SDK 暴露标准工具。

> 当前语料、公司、制度、型号、错误码含义和金额均为合成演示数据。共享集合上的元数据过滤不等于物理隔离，也不代表生产级 IAM。

## 核心链路

```text
服务端演示身份
      │
      ├─ tenant / department / role / clearance 过滤
      │
查询 ─┼─ Dense Top-15 ──┐
      │                 ├─ Qdrant RRF ─→ Cross-Encoder ─→ Top-5 ─→ MCP Tool
      └─ BM25 Top-15 ───┘
```

## 环境

项目固定使用 Python 3.11。当前工作区使用项目内 uv 和虚拟环境，不要求替换系统 Python。

```powershell
$env:PYTHONPATH=(Resolve-Path 'var/uv-bootstrap').Path
$env:UV_PYTHON_INSTALL_DIR=(Resolve-Path 'var/python').Path
$env:UV_CACHE_DIR=(Resolve-Path 'var/uv-cache').Path
python -m uv sync
```

模型默认下载到 `var/models/`，Qdrant Local 数据写入 `var/qdrant/`。

## 数据与身份

- `data/mock_docs/`：15 篇合成企业文档；
- `data/benchmark.jsonl`：48 条固定评测题；
- `config/principals.yaml`：8 个服务端演示身份；
- `scripts/validate_materials.py`：材料一致性检查。

身份在服务进程启动时通过 `SECURERAG_PRINCIPAL_ID` 绑定。MCP 工具不接受 `role`、`tenant_id` 或 `clearance` 参数。

## 入库

```powershell
.\.venv\Scripts\python.exe -m secure_rag.ingestion --rebuild
```

入库前会执行材料一致性检查。`--rebuild` 显式重建集合；Point ID 由稳定 Chunk ID 确定性生成。

## 本地检索

```powershell
.\.venv\Scripts\python.exe -m secure_rag.cli `
  "ERR_GATEWAY_502_DB 的第一步排查是什么？" `
  --principal engineer-demo `
  --mode hybrid_rerank
```

可用模式：`dense`、`sparse`、`hybrid_rrf`、`hybrid_rerank`。

## MCP stdio 服务

```powershell
$env:SECURERAG_PRINCIPAL_ID='engineer-demo'
.\.venv\Scripts\python.exe -m secure_rag.server
```

工具：

```text
search_knowledge_base(query: str, top_k: int = 5)
```

调用方只能提交问题和结果数量，不能通过工具参数切换身份。

## 测试与评测

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m secure_rag.evaluation
$env:SECURERAG_RERANK_ENABLED="true"
.\.venv\Scripts\python.exe -m secure_rag.evaluation --report-name p1_final
```

评测结果写入：

- `reports/latest.json`：逐查询机器可读结果；
- `reports/latest.md`：适合 README/CV 复核的汇总。
- `reports/p1_final.json` / `.md`：48 题四模式最终消融结果。

指标包括 Hit@1、Hit@3、Recall@3、MRR@5、nDCG@5 和未授权候选率。安全用例同时检查 Dense、Sparse、Hybrid RRF 和 Hybrid Rerank 最终结果。

## 当前实测结果

2026-10-22 在项目内 Python 3.11.17 环境完成首轮 P0 验证：

- 15 篇文档生成并持久化为 15 个 Chunk/Point；
- 18 条正例查询中，Dense 与 Hybrid 的 Hit@1、Hit@3、Recall@3、MRR@5 均为 1.000；
- Sparse 在 6 条精确实体查询上的上述指标均为 1.000，在语义和普通问题上为 0；
- 6 条安全查询覆盖 Dense、Sparse、Hybrid，共检查 50 个返回候选，未授权候选为 0；
- 官方 MCP 客户端通过 stdio 发现并调用 `search_knowledge_base`；
- MCP 工具输入仅有 `query` 与 `top_k`，低权限进程的伪造角色查询未返回高密级文档。

详见 [`reports/latest.md`](reports/latest.md)。当前合成集较小，Dense 已达到满分，因此不能据此宣称 Hybrid 相比 Dense 获得了百分比提升；现阶段能证明的是两路检索的互补行为、权限边界和端到端可运行性。

同日完成 P1-B：将评测集扩展到 48 题，其中 36 条正例覆盖困难干扰与双文档比较，12 条用于越权边界。`BAAI/bge-reranker-base` 对已授权的 RRF Top 15 候选重排后，Hit@1 从 Hybrid RRF 的 0.917 提升至 1.000，MRR@5 从 0.958 提升至 1.000，nDCG@5 从 0.969 提升至 1.000；12 条越权题在四种模式中共检查 148 个返回候选，未授权候选为 0。详见 [`reports/p1_final.md`](reports/p1_final.md)。

MCP Tool schema、stdio 调用和服务端身份绑定已使用官方客户端验证，并在普通 PowerShell 中完成 P1 环境复跑。修正首次 Inspector 配置后，工程师困难题与实习生越权题均以 `hybrid_rerank` 执行、无降级警告，并已归档请求界面与完整响应；详见 [`reports/mcp_evidence.md`](reports/mcp_evidence.md)。

## 当前边界

- 首版只实现检索层，不在服务端生成最终回答；
- Cross-Encoder 已实现但默认关闭；暂不包含 Ragas、HTTP 认证、Docker 或 Web UI；
- 指标只描述当前小规模合成数据集；
- 共享 Qdrant 集合上的元数据过滤不是物理隔离，未授权候选率为 0 也不是普遍安全证明；
- 后续带引用问答遵循 `docs/问答与配置约定.md`。
