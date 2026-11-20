# 深度登记 听证采纳勘误册

- 规模：中型
- 核心规则：稳定段落锚点沿版本树追踪位置和内容，归并复述仍保留全量来源，各分支采纳不一致时待审。
- 使用者：听证文书组审定段落、意见与勘误寄送单。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 文书版本 | 列出文书链和末版 | `GET /api/versions/{sample}` | `app/modules/m1_versions/rules.py` | `tests/test_versions.py` |
| M2 页码锚点 | 核验移页、录入和删段操作 | `GET /api/anchors/{sample}` | `app/modules/m2_anchors/rules.py` | `tests/test_anchors.py` |
| M3 发言识别 | 核实登记号、姓名和别名 | `GET /api/speakers/{sample}` | `app/modules/m3_speakers/rules.py` | `tests/test_speakers.py` |
| M4 修订链路 | 从原段追到文书末版 | `GET /api/revisions/{sample}` | `app/modules/m4_revisions/rules.py` | `tests/test_revisions.py` |
| M5 意见归并 | 检视意见组的所有原始来源 | `GET /api/opinions/{sample}` | `app/modules/m5_opinions/rules.py` | `tests/test_opinions.py` |
| M6 采纳核对 | 并列比对分支结论和来源总账 | `GET /api/adoption/{sample}` | `app/modules/m6_adoption/rules.py` | `tests/test_adoption.py` |
| M7 勘误寄送 | 将可寄送和暂缓草案按收件人生成 | `GET /api/mailings/{sample}` | `app/modules/m7_mailings/rules.py` | `tests/test_mailings.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-07 | 脏样例：寄送地址是占位符 | 生成无效寄送单 | 地址校验失败后暂缓 | `app/modules/m7_mailings/rules.py` | `tests/test_mailings.py::test_missing_address_holds` |
| TRAP-11 | 干净样例：发布时间有时区偏移 | 按文字排序误判 | 按 UTC 时间核验 | `app/modules/m1_versions/rules.py` | `tests/test_versions.py::test_timestamps_by_instant` |
| TRAP-13 | 干净样例：后版在输入靠前 | 误判找不到前版 | 按前版关系拓扑排序 | `app/modules/m1_versions/rules.py` | `tests/test_versions.py::test_out_of_order_versions` |
| TRAP-14 | 脏样例：同版同锚点收到两道指令 | 写入顺序决定页码 | 隔离冲突并保留两条来源 | `app/modules/m2_anchors/rules.py` | `tests/test_anchors.py::test_duplicate_anchor_quarantined` |
| TRAP-19 | 脏样例：同一意见有不同采纳结论 | 采用最后修订意见 | 保留矩阵并待审 | `app/modules/m6_adoption/rules.py` | `tests/test_adoption.py::test_forked_decision_review` |
| TRAP-20 | 脏样例：修订互相指向 | 遍历不结束 | 找出环并隔离 | `app/modules/m1_versions/rules.py` | `tests/test_versions.py::test_cycle_isolated` |
| TRAP-21 | 干净样例：指向缺失前版 | 误作首版投入核算 | 隔离断链版本 | `app/modules/m1_versions/rules.py` | `tests/test_versions.py::test_missing_parent` |
| TRAP-22 | 干净样例：说话人使用登记别名 | 新增重复发言人 | 以已登记别名回溯编号 | `app/modules/m3_speakers/rules.py` | `tests/test_speakers.py::test_alias_resolution` |

## 对账规则

原段输入总数等于有效意见主行、复述与修订来源、争议来源之和。每条参与对勘的行可见原文与表内位置。

## 已知边界

输入是文书组已抽取的结构化记录。人工指定主题及锚点。递交草案与原证据供外部流程使用。
