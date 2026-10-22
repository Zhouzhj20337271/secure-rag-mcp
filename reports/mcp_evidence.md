# MCP 调用证据与复跑状态

## 已验证证据

2026-10-22 的 P0 smoke test 使用官方 MCP Python Client 通过 stdio 启动 `secure_rag.server`，完成了以下断言：

- 成功发现 `search_knowledge_base`；
- Tool 输入 schema 仅暴露 `query` 与 `top_k`，调用方不能提交 tenant、department、role 或 clearance；
- `engineer-demo` 查询 `ERR_GATEWAY_502_DB` 时返回 `ops-001`；
- `intern-demo` 伪称总经理查询管理层激励方案时，`exec-001` 未进入返回结果。

可复跑脚本：`scripts/smoke_mcp.py`。

## P1-B 本轮状态

本轮 `hybrid_rerank` 已通过真实 CLI 查询和 48 题离线评测验证，但当前 Codex 沙箱内复跑子进程 stdio 时停在 MCP 握手阶段；直接检索、模型推理和 Qdrant 均正常。该次尝试未被记录为 MCP 通过，也未伪造调用结果。

因此当前证据边界是：

- MCP Tool schema、stdio 调用和服务端绑定身份：已在 P0 验证；
- Cross-Encoder 重排、分数返回、权限过滤和降级逻辑：已在 P1 评测与 CLI 验证；
- 启用重排后的 stdio 再验证：建议在普通 PowerShell或 MCP Inspector 中复跑并截图。
