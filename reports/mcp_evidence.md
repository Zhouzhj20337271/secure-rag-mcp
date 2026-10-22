# MCP 调用证据与复跑状态

## 已验证证据

2026-10-22 的 P0 smoke test 使用官方 MCP Python Client 通过 stdio 启动 `secure_rag.server`，完成了以下断言：

- 成功发现 `search_knowledge_base`；
- Tool 输入 schema 仅暴露 `query` 与 `top_k`，调用方不能提交 tenant、department、role 或 clearance；
- `engineer-demo` 查询 `ERR_GATEWAY_502_DB` 时返回 `ops-001`；
- `intern-demo` 伪称总经理查询管理层激励方案时，`exec-001` 未进入返回结果。

可复跑脚本：`scripts/smoke_mcp.py`。

## P1-B 本轮状态

用户随后于普通 PowerShell 中设置 `SECURERAG_RERANK_ENABLED=true`、`HF_HUB_OFFLINE=1` 和 `TRANSFORMERS_OFFLINE=1`，执行 `scripts/smoke_mcp.py`，获得：

```text
PASS MCP stdio: tools=['search_knowledge_base'] parameters=['query', 'top_k'] engineer=['ops-001', 'ops-003', 'ops-002'] intern=['public-003', 'public-001', 'public-002']
```

该结果补齐了官方 MCP Client 的 stdio 复跑证据：Tool 发现与 schema 正确，工程师查询命中 `ops-001`，低权限身份未返回 `exec-001`。旧版 smoke 脚本没有在输出中单独打印实际模式和降级警告，因此现已升级脚本：启用重排时会额外断言并输出 `hybrid_rerank`，任何 RRF 降级都会失败。

首次 Inspector 导出曾显示旧的 `hybrid_rrf` 模式和错误身份，未被计为通过。修正输入方式、关闭旧实例并分别以工程师/实习生身份重启后，最终 Inspector 证据验证通过：

- 工程师困难题返回 `principal_id=engineer-demo`、`retrieval_mode=hybrid_rerank`、`warning=null`；
- `ops-002` 的 RRF 分数为 `0.3333`，经 Cross-Encoder 重排后以 `2.3477` 排名第 1，证明重排改变了原始融合顺序；
- 实习生越权题返回 `principal_id=intern-demo`、`retrieval_mode=hybrid_rerank`、`warning=null`；
- 实习生结果仅包含三个 public 文档，禁止目标 `exec-001` 未进入候选；
- 两个响应均返回 `rrf_score` 和 `rerank_score`，`result_count=3`。

归档证据：

- `reports/evidence/mcp_engineer_hard_query.json`
- `reports/evidence/mcp_intern_denied.json`
- `reports/evidence/mcp_inspector_engineer.png`
- `reports/evidence/mcp_inspector_intern.png`

因此当前证据边界是：

- MCP Tool schema、stdio 调用和服务端绑定身份：已在 P0 及普通 PowerShell 复跑中验证；
- Cross-Encoder 重排、分数返回、权限过滤和降级逻辑：已在 P1 评测与 CLI 验证；
- Inspector 图形化调用、工程师重排示例和实习生越权边界：已验证并归档。
