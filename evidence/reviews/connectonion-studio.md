# ConnectOnion Studio: Review Decision

日期：2026-09-18  
审核人：Evan  
状态：`confirmed_public`

关联公开记录：[ConnectOnion Studio](../registry/approved/project-connectonion-studio.json)。本文件是人工审核记录。

## 确认的项目定位

ConnectOnion 是可创建和运行 agents 的后端框架。ConnectOnion Studio 将原本以命令行为主的 agent 管理操作可视化，提供本地 Agent 管理与开发界面；每个 agent 使用相互隔离的工作目录。ConnectOnion iOS 则作为移动端客户端，连接已创建的 agent，支持对话、资料检索、文件处理与结果返回。

## 批准的公开 claims

| ID | 批准内容 | 个人贡献 | 公开来源 |
| --- | --- | --- | --- |
| CO-01 | Studio 是一个本地 Agent 管理与开发工具，支持创建、运行、诊断 agent、QR 连接、实时状态和日志。 | 项目事实 | public README / repository |
| CO-02 | Evan 负责将 ConnectOnion 的命令式 agent 管理能力产品化为 Studio 的可视化工作流，并实现每个 agent 的隔离工作区。 | 已由 Evan 确认 | public repository；后续补充模块级代码定位 |
| CO-03 | Evan 负责 Studio 的 skills market / 安装工作流、per-agent skill 配置与相应 API。 | 已由 Evan 确认 | public repository / skills store commit |
| CO-04 | Evan 负责 Studio 的 FastAPI、WebSocket、QR 连接、macOS 壳与 agent lifecycle 管理模块。 | 已由 Evan 确认 | public README / repository；后续补充模块级代码定位 |
| CO-05 | Evan 修复了 invite-code 验证中的 YAML 类型转换问题：数值或 YAML 关键字可能被解析为非字符串，而移动端提交的是字符串，导致等值邀请码无法匹配。 | 已由 Evan 确认 | public commit `d320687` |

## 对外优先表述

```text
我把 ConnectOnion 的命令式 Agent 管理能力做成了一个本地可视化开发工具 ConnectOnion Studio。它支持创建、运行和诊断 agents，并为每个 agent 隔离工作区；我负责 FastAPI、实时状态/日志、QR 连接、macOS 客户端封装，以及 skills 工作流和连接信任相关的工程实现。

ConnectOnion iOS 是与 Studio 配套的移动端客户端，用于连接已经创建的 agent，完成对话、资料检索和文件处理等任务。
```

## 已知边界

- 公开问答可以讲产品架构、已批准模块和公开仓库中可定位的实现，不输出 identity、key、用户本地 workspace 内容或局域网地址。
- 对“全部由我独立完成”的泛化表述，优先改为上表中已确认的模块职责；若面试官追问，再检索对应公开代码、commit 和 README。
- ConnectOnion iOS 的个人贡献将在单独审核后写入其 review decision，不能因 Studio 审核自动扩展。
