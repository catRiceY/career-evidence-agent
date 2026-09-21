# ConnectOnion iOS: Review Decision

日期：2026-09-18  
审核人：Evan  
状态：`confirmed_public`（IOS-01 至 IOS-07）；IOS-08 `exclude`。

关联公开记录：[ConnectOnion iOS](../registry/approved/project-connectonion-ios.json)。该项目是团队项目；公开表达必须区分项目事实与 Evan 已确认的个人模块。

## 批准的公开 claims

| ID | 批准内容 | 类型与边界 |
| --- | --- | --- |
| IOS-01 | ConnectOnion iOS 是 ConnectOnion Agent 的 SwiftUI 移动端客户端，用于连接已创建的 Agent，支持实时对话、工具调用展示、审批、Agent 状态查看及文件/图片输入。 | 项目事实 |
| IOS-02 | Evan 负责移动端与 Agent 的连接可靠性和异常恢复体验，包括断线重连、Agent 未运行、设备离线、连接被拒绝、会话恢复与重新提问等场景。 | 已确认个人贡献 |
| IOS-03 | Evan 将底层网络/协议错误映射为用户可理解且可行动的提示，区分设备离线、Agent 未启动、地址不可达和连接被拒绝等情况。 | 已确认个人贡献 |
| IOS-04 | Evan 实现或维护 Agent 回复中的 Markdown 图片渲染：解析独立图片块、异步加载图片，并对不安全或加载失败的链接提供可解释提示。 | 已确认个人贡献 |
| IOS-05 | 客户端与 Python Agent 通过 WebSocket 建立连接，使用 Ed25519 签名握手，并以结构化事件流传递文本、工具调用、审批和计划确认等内容。 | 项目协议事实；不自动归因为 Evan 独立实现 |
| IOS-06 | 项目采用 Core / Features 分层，Core 负责网络、加密、数据和聊天逻辑，Features 负责 Chat、Composer、Agents 等产品界面，并通过 protocol + concrete + mock 保持可测试性。 | 项目架构事实；Evan 的具体层职责待单独确认 |
| IOS-07 | 项目包含 unit、UI 和真实 App ↔ live Agent 的 E2E 测试链路。 | 项目测试事实；不公开未经核实的测试数量、覆盖率或 CI 指标 |

## 明确排除

| ID | 内容 | 原因 |
| --- | --- | --- |
| IOS-08 | “Evan 独立完成 iOS App 的全部 UI、协议、加密、数据、Widget、Live Activity 与测试”。 | 过于泛化，不能代表团队项目的准确贡献边界。 |

## 对外优先表述

```text
ConnectOnion iOS 是与 ConnectOnion Agent 配套的 SwiftUI 移动端客户端，用于连接已创建的 Agent，支持实时对话、工具调用和审批等交互。我重点负责连接可靠性和异常恢复，例如区分设备离线、Agent 未运行、连接被拒绝等状态，并处理断线后的会话恢复和重新提问；我也实现了 Agent 回复中 Markdown 图片等富内容的可解释展示。
```

## 公开边界

- 可讨论公开 README、已批准的个人模块、协议的架构级说明和公开 commit 所支持的排障案例。
- 不把项目整体架构、Ed25519、Widget、Live Activity 或测试链路自动归为 Evan 独立完成。
- 不输出身份密钥、真实 endpoint、用户数据或未确认的测试量化指标。
