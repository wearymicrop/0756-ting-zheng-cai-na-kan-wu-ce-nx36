# 听证采纳勘误册

文书组按稳定段落锚点核对原页与末版页码，核实发言人、复述来源与采纳意见，再生成可供人工复核的寄送单。

```sh
docker compose up --build
```

访问 `http://127.0.0.1:18450`，从「修订链路」选择锚点。脏样例中的 `A-08` 在一条分支被删除，`A-01` 页码一致但采纳结论冲突，分别在「修订链路」和「采纳核对」查看。归档案卷后可下载证据。

`docker compose exec -T app pytest -q` 运行测试。命名卷 `records` 保存归档，宿主可用 `DB_PATH` 指定 SQLite 文件。宿主先安装 `requirements.txt`，再执行 `uvicorn app.main:app --port 18450`。

- [七个模块与陷阱](docs/DEPTH.md)
- [字段与修订规则](docs/DATA-DICTIONARY.md)
- [接口与证据](docs/API.md)
