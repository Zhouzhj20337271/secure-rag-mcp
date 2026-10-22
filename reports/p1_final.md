# SecureRAG-MCP 固定基准评测

- Dense：`BAAI/bge-small-zh-v1.5`
- Sparse：`Qdrant/bm25`
- Reranker：`BAAI/bge-reranker-base`
- 正例查询：36

## 检索指标

| 模式 | 分组 | Hit@1 | Hit@3 | Recall@3 | MRR@5 | nDCG@5 |
|---|---|---:|---:|---:|---:|---:|
| dense | dev | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | test | 0.833 | 1.000 | 1.000 | 0.917 | 0.938 |
| dense | exact | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | semantic | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | ordinary | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | hard | 0.750 | 1.000 | 1.000 | 0.875 | 0.908 |
| dense | comparison | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | all | 0.917 | 1.000 | 1.000 | 0.958 | 0.969 |
| sparse | dev | 0.222 | 0.333 | 0.333 | 0.278 | 0.292 |
| sparse | test | 0.278 | 0.278 | 0.250 | 0.278 | 0.256 |
| sparse | exact | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| sparse | semantic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| sparse | ordinary | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| sparse | hard | 0.083 | 0.250 | 0.250 | 0.167 | 0.188 |
| sparse | comparison | 0.333 | 0.333 | 0.250 | 0.333 | 0.269 |
| sparse | all | 0.250 | 0.306 | 0.292 | 0.278 | 0.274 |
| hybrid_rrf | dev | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rrf | test | 0.833 | 1.000 | 1.000 | 0.917 | 0.938 |
| hybrid_rrf | exact | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rrf | semantic | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rrf | ordinary | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rrf | hard | 0.750 | 1.000 | 1.000 | 0.875 | 0.908 |
| hybrid_rrf | comparison | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rrf | all | 0.917 | 1.000 | 1.000 | 0.958 | 0.969 |
| hybrid_rerank | dev | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | test | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | exact | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | semantic | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | ordinary | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | hard | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | comparison | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid_rerank | all | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## 权限安全检查

- 安全查询数：12
- 检查模式：dense, sparse, hybrid_rrf, hybrid_rerank
- 返回候选总数：148
- 未授权候选数：0
- 未授权候选率：0.000000
- 出现越权的查询/模式组合：0

> 该结果只覆盖当前小规模合成测试集，不代表生产环境的普遍安全证明。
