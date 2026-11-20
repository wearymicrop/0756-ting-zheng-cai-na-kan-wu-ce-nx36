# 接口与证据

- `GET /api/health` 返回项目和规则版本。
- `GET /api/{模块}/{样例}` 单独计算到该阶段。模块与样例见深度登记。
- `POST /api/runs` 接收 `{"sample":"clean"}`、`{"sample":"dirty"}` 或 `{"data":{…}}`，返回完整计算和归档 ID。
- `GET /api/runs/{id}` 查询不可变归档。`POST /api/runs/{id}/rerun` 用归档输入与当前规则运行。相同规则与来源复用原记录。
- `GET /api/runs/{id}/export` 下载 JSON 证据。内含批次设置、各输入表、原行号、各阶段计算及规则版本。

## 旧案卷影响册（M8）

- `POST /api/runs/{id}/impact/recompute` 用当前规则重算旧归档；请求体可空，或带 `{"supplement":{…}}` 合并下午补交件（只允许追加 versions/passages/directory/decisions 或更新 config）。返回整册：`summary` 计数、`entries` 逐条维持/追补/撤回、`recipients` 待补寄与撤回对象、`revision` 册版本号。
- `GET /api/runs/{id}/impact` 读取最近一版影响册；尚未重算返回 404。
- `POST /api/runs/{id}/impact/dispatch` 登记已送达勘误（先发），请求体 `{"opinion_ids":[…]}`，留空表示登记全部当前可寄送条目。送达结论与页码快照只追加、不可改写，并立即重算影响册。

影响册条目以意见稳定键对齐，重跑不新增重复行；`dispatches` 表只追加，`impacts` 表按案卷单事务整册替换，提交前异常会回滚到上一版。工作台页面为 `GET /work/impact?sample=…&run=…`（不带 run 时自动把当前样例归档为基线）。

行号从 1 开始，按各 JSON 数组的位置计。归档键由项目、规则版本、来源名和规范化输入 JSON 计算。输入摘要为规范化 JSON 的 SHA-256。耗时与生成时刻只在首次提交时落库，便于重启后比较同一份记录。
