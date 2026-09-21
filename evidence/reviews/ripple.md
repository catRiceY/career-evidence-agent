# RiPPLE: Review Decision

日期：2026-09-18  
审核人：Evan  
状态：`confirmed_public`（仅限已确认的公开论文事实）

关联公开记录：[RiPPLE](../registry/approved/paper-ripple.json)。公开来源为 [arXiv:2609.12418](https://arxiv.org/abs/2609.12418)。

## 批准的公开 claims

| ID | 批准内容 | 边界 |
| --- | --- | --- |
| RIPPLE-01 | Evan（Yifan Yang）是 *RiPPLE: Cross-Space Performance Prediction from Early Training for Neural Architecture Search* 的并列第一作者。 | 原件首页以 `*` 标注共同贡献；不由此推断具体个人分工。 |
| RIPPLE-02 | RiPPLE 只训练一小组覆盖性 anchor 到早期阶段，将曲线外推成替代标签，并把这些标签传播到不需训练的特征上，用有限预算为整个 NAS 搜索空间排序。 | abstract-level 方法说明。 |
| RIPPLE-03 | 方法的关键设计是：早期训练信号只作为少量 anchor 的标签，而不是每个待预测候选都需要获得的特征，因此训练成本随 anchor 数量而非整个搜索空间扩张。 | 不把摘要中的实验结论扩展为对任何数据集的保证。 |
| RIPPLE-04 | 论文的公开预印本为 arXiv v1（2026-09-11）。目前计划投稿 CVPR 2027，但尚未提交。 | 禁止写成 “CVPR 2027 under submission / in review”。 |

## 待确认的个人贡献

论文为共同一作不等同于每一项工作均由 Evan 完成。待 Evan 以自然语言补充后，再增加关于方法、理论、代码、实验、写作等的个人 contribution claim。

## 对外优先表述

```text
我是 RiPPLE 的并列第一作者。它解决的是 NAS 中“准确评估很贵”的问题：只训练少量有代表性的架构到早期阶段，将这些早期曲线外推为替代标签，再把信号传播到全体候选，从而在有限预算下完成跨搜索空间的性能排序。该工作目前已公开为 preprint；CVPR 2027 是计划投稿方向，尚未提交。
```

## 公开边界

- 可公开题名、并列一作身份、arXiv 链接、摘要级方法和准确的当前状态。
- 不从并列一作身份推断 Evan 的具体分工；该部分等待本人确认。
- 不称 CVPR 2027 已投稿、在审或接收。
