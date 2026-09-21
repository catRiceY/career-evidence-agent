# CoRA-NAS: Review Decision

日期：2026-09-18  
审核人：Evan  
状态：`confirmed_public`（仅限已确认的公开论文事实）

关联公开记录：[CoRA-NAS](../registry/approved/paper-cora-nas.json)。公开来源为 [arXiv:2609.11884](https://arxiv.org/abs/2609.11884)。

## 批准的公开 claims

| ID | 批准内容 | 边界 |
| --- | --- | --- |
| CORA-01 | Evan（Yifan Yang）是 *CoRA-NAS: Coarse Ranking and Anchor-Residual Refinement for Neural Architecture Search* 的并列第一作者。 | 原件首页以 `*` 标注共同贡献；不由此推断具体个人分工。 |
| CORA-02 | CoRA-NAS 面向低成本 NAS 排序：先将多种零成本 proxy 的排序合并为粗排，再以少量 anchor 的早期训练曲线进行残差修正。 | abstract-level 方法说明。 |
| CORA-03 | 该方法将额外训练开销控制在约完整训练预算的 1%，并避免使用完整训练的 architecture-accuracy 标签来拟合其排序器。 | 这是论文摘要的范围说明，不外推为所有 NAS 场景的普适结论。 |
| CORA-04 | 论文的公开预印本为 arXiv v1（2026-09-10）。 | 当前仅称公开 preprint；尚未批准声称任何未确认 venue/status。 |

## 待确认的个人贡献

论文为共同一作不等同于每一项工作均由 Evan 完成。待 Evan 以自然语言补充后，再增加关于方法、理论、代码、实验、写作等的个人 contribution claim。

## 对外优先表述

```text
我是 CoRA-NAS 的并列第一作者。这个工作关注一个高成本问题：怎样不把每个候选网络都训练到收敛，仍然对架构进行可靠排序。方法先综合零成本信号形成粗排，再只对少量代表性架构读取早期训练曲线进行修正，把额外训练预算压到完整训练的大约 1%。
```

## 公开边界

- 可公开题名、并列一作身份、arXiv 链接、摘要级方法与论文中已公开的范围描述。
- 不从并列一作身份推断 Evan 的具体分工；该部分等待本人确认。
- 不虚构投稿、接收、代码开放或性能承诺。
