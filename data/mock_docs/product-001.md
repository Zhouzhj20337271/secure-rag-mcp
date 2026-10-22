---
document_id: product-001
title: NX-2400 网关升级手册
tenant_id: aster-demo
department: engineering
clearance_level: internal
clearance_rank: 2
allowed_roles: [engineer]
document_type: manual
---
# NX-2400 网关升级手册

本文属于虚构企业演示数据。NX-2400 的演示目标固件版本为 2.4.3。升级前备份配置，并确认设备处于双节点健康状态。

先升级备用节点，进行连通性验证后切换流量，再升级原主节点。若升级后连续三次健康检查失败，回滚至备份版本并恢复配置。不得同时重启两个节点。
