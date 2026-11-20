# 数据字典

| 输入表 | 关键字段 | 含义 |
|---|---|---|
| config | docket、root | 听证案号与唯一首版号 |
| versions | version、parent、published_at、pages | 前版号可空，发布时间带偏移，页数为正整数，单案最多 128 个版本 |
| passages | version、anchor、op、page | 锚点是稳定字符串。新增或全文修订 `upsert`，单独移页 `move`，删段 `delete`。删段页码为空 |
| passages | speaker_id、speaker、topic、position、text | `upsert` 填写登记号或姓名、标准议题、立场、原话。立场为 `support`、`oppose` 或 `amend` |
| directory | id、name、aliases、contact | 发言人登记号、登记姓名、别名数组、寄送地址。显式登记号与附带姓名须相符 |
| decisions | version、anchor、result | 结论为 `accepted`、`rejected` 或 `partial`，须指向该版保留的段落 |

版本由前一版指针决定，发布时刻标准化到 UTC 用于核验，晚出的分支不会覆盖同级分支。各版继承前版段落，移页保留内容来源。全文改写后只继承该次改写至末版之间的采纳结论。任一末版的页码、内容、删除状态或适用结论不一致时保留各分支并待审。同名时按登记号区分，无号同名进入争议。仅当已识别登记号、规范化标准议题及立场相同才归为复述。主题名与锚点由文书人员标定，系统保留原话及每一个来源行。

`effective` 是核实意见的主行，`repetition` 包含复述及同组移页、修订证据，`disputed` 为归属或结论待核的原始行。每条段落输入只能进入一个分类，决定和名册行另按表留证。生成按收件人归并的寄送草案，地址与结论均核实才能标记可寄送。系统只生成草案。
