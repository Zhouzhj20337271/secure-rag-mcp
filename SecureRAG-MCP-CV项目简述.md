# SecureRAG-MCP：CV 项目简述

> 本版本只写已经落地并保存证据的功能与实验结果；评测对象为本地合成企业知识库，不代表生产规模。

## 简历可直接粘贴版

### SecureRAG-MCP：权限感知混合检索与 Agent 知识库服务

**独立开发｜2026.10—至今**  
**技术栈：** Python 3.11、MCP Python SDK、Qdrant、FastEmbed、BGE、BM25、RRF、Cross-Encoder、Pytest

**项目描述：** 面向企业知识库中专有实体与语义问题混合召回、敏感文档越权访问及 Agent 接入协议不统一等问题，开发权限感知的本地混合检索服务，并通过 MCP Tool 向智能体客户端提供结构化知识检索能力。

- **混合检索与融合：** 基于 Qdrant 构建 BGE Dense 与 BM25 Sparse 双路召回，使用原生 RRF 融合 Top 15 候选，兼顾错误码、制度编号、产品型号等精确实体与中文语义改写问题。
- **Cross-Encoder 重排：** 使用 `BAAI/bge-reranker-base` 对已授权的 RRF 候选进行二阶段重排，同时保留融合分数与重排分数；在 36 条正例中将 Hybrid RRF 的 Hit@1 从 91.7% 提升至 100%，MRR@5 从 95.8% 提升至 100%。
- **检索前权限过滤：** 建立 tenant、department、role、clearance 四维权限策略，由服务端绑定可信演示身份并生成 Qdrant 元数据过滤条件，避免未授权文档进入 Dense、Sparse、RRF 或重排候选；12 条越权题覆盖四种模式，共检查 148 个返回候选，未授权候选率为 0。
- **MCP 服务与评测：** 将管线封装为 `search_knowledge_base(query, top_k)`，返回来源、权限标签、RRF 与重排分数；使用官方 MCP Client 完成 stdio Tool 发现与权限边界验证，并建立 48 题固定评测集及四模式消融报告。

## 更短的一页简历版

- 使用 Qdrant + FastEmbed 实现 BGE Dense、BM25 Sparse、RRF 融合与 Cross-Encoder 重排的两阶段检索链路；在 36 条合成正例中将 Hit@1 从 91.7% 提升至 100%、MRR@5 从 95.8% 提升至 100%。
- 设计 tenant/department/role/clearance 四维检索前权限过滤与服务端身份绑定，在 12 条越权题、四种检索模式的 148 个返回候选中保持未授权候选率为 0。
- 将检索服务封装为参数受限的 MCP Tool，返回引用来源、融合/重排分数和权限标签，并通过官方 MCP Client 验证 stdio 调用与低权限访问边界。

## 指标口径与面试边界

- 总计 48 条合成查询：36 条正例、12 条越权题；正例覆盖精确实体、语义改写、普通问题、困难干扰和双文档比较。
- 91.7%→100% 与 95.8%→100% 比较的是同一固定集合上的 `Hybrid RRF` 与 `Hybrid + Reranker`，不是线上 A/B 实验。
- “未授权候选率为 0”只指当前测试集，不代表形式化安全证明；Qdrant 元数据过滤也不等同于物理隔离。
- 可以使用“企业知识库场景”“多租户权限模型”“标准化 Agent 接入”等架构性表述；不写“生产上线”“百万文档”“高并发”或未实施的 Ragas、Docker、Web UI。

## 面试演示顺序

1. 精确错误码查询，展示 Dense、Sparse 和 RRF 候选。
2. 运行带干扰词的问题，展示 Cross-Encoder 将正确文档从第 2 位提升到第 1 位。
3. 切换到低权限服务端身份，展示机密目标不会进入候选。
4. 使用 MCP 客户端调用 `search_knowledge_base`，说明调用方为何不能提交 role 或 tenant。
5. 打开 `reports/p1_final.md`，解释消融指标、三条被重排纠正的困难题及实验局限。
