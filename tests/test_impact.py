"""旧案卷影响册（M8）测试。

对应用户要求：
- 规则更新后旧勘误逐条给出维持 / 追补 / 撤回及受影响收件人；
- 同一案卷重跑不新增重复结果（稳定键幂等）；
- 已送达记录只追加、原结论冻结、数据不丢失；
- 重算中断事务回滚，恢复旧版影响册；
- 下午补交采纳决定可改变待补寄对象。
"""
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import settings
from app.modules.m8_impact import service
from app.pipeline import calculate
from app.samples import load_sample


@pytest.fixture
def version_bump(monkeypatch):
    """模拟规则升级：先在 1.0.0 下归档，再切到 2.0.0 重算。"""
    monkeypatch.setattr(settings, "RULE_VERSION", "1.0.0")
    yield
    monkeypatch.setattr(settings, "RULE_VERSION", "2.0.0")


def archive_baseline(client, payload):
    return client.post("/api/runs", json=payload).json()


def test_same_rule_recompute_all_maintain(client, version_bump):
    baseline = archive_baseline(client, {"sample": "clean"})
    settings.RULE_VERSION = "2.0.0"
    first = client.post(f"/api/runs/{baseline['id']}/impact/recompute").json()
    second = client.post(f"/api/runs/{baseline['id']}/impact/recompute").json()
    assert first["summary"] == {"total": 6, "maintain": 6, "supplement": 0, "withdraw": 0,
                                "served": 0, "pending": 6, "changed": False}
    # 重算不新增重复条目：稳定键唯一，且两次结果完全一致。
    keys = [entry["key"] for entry in second["entries"]]
    assert len(keys) == len(set(keys)) == 6
    assert first["entries"] == second["entries"]
    assert second["revision"] == 2
    assert first["baseline_rule_version"] == "1.0.0" and second["current_rule_version"] == "2.0.0"


def test_page_change_triggers_supplement(client, version_bump):
    baseline = archive_baseline(client, {"sample": "clean"})
    settings.RULE_VERSION = "2.0.0"
    response = client.post(f"/api/runs/{baseline['id']}/impact/recompute", json={"supplement": {
        "passages": [{"version": "V3", "anchor": "A-03", "op": "move", "page": 10}],
    }}).json()
    changed = [entry for entry in response["entries"] if entry["outcome"] == "supplement"]
    assert len(changed) == 1 and changed[0]["changed_fields"] == ["pages"]
    recipient = response["recipients"][0]
    assert recipient["speaker_id"] == "P002" and recipient["actions"] == ["supplement"]
    assert recipient["state"] == "ready"  # 地址与结论均仍核实，可直接补寄


def test_replaced_decision_changes_mailing_target(client, version_bump):
    """下午补交采纳决定：确定结论之间的变化形成追补单，待补寄对象随之改变。"""
    data = load_sample("clean")
    data["decisions"] = [row for row in data["decisions"]
                         if not (row["version"] == "V1" and row["anchor"] == "A-08")]
    data["decisions"].append({"version": "V1", "anchor": "A-08", "result": "partial"})
    baseline = archive_baseline(client, {"data": data})
    settings.RULE_VERSION = "2.0.0"
    client.post(f"/api/runs/{baseline['id']}/impact/recompute")
    client.post(f"/api/runs/{baseline['id']}/impact/dispatch")

    new_data = {**data, "decisions": [
        row for row in data["decisions"] if not (row["version"] == "V1" and row["anchor"] == "A-08")
    ] + [{"version": "V1", "anchor": "A-08", "result": "rejected"}]}
    store = client.app.state.archive
    register = service.build_register(store.get(baseline["id"]), calculate(new_data),
                                      store.list_dispatches(baseline["id"]))
    entry = next(row for row in register["entries"] if row["topic"] == "绿带")
    assert (entry["outcome"], entry["old_verdict"], entry["new_verdict"]) == (
        "supplement", "partial", "rejected")
    assert entry["served"] and entry["action"] == "notice_supplement" and entry["served_locked"]
    assert register["recipients"][0]["speaker_id"] == "P001"


def test_served_records_are_frozen_and_never_lost(client, version_bump):
    baseline = archive_baseline(client, {"sample": "clean"})
    run_id = baseline["id"]
    settings.RULE_VERSION = "2.0.0"
    client.post(f"/api/runs/{run_id}/impact/recompute")
    dispatch = client.post(f"/api/runs/{run_id}/impact/dispatch").json()
    assert dispatch["newly_recorded"] == 6 and dispatch["total_served"] == 6
    # 重复登记幂等：不产生重复台账行。
    again = client.post(f"/api/runs/{run_id}/impact/dispatch").json()
    assert again["newly_recorded"] == 0 and again["total_served"] == 6

    # 重算导致撤回：已送达条目只出撤回单，冻结的原结论仍在。
    client.post(f"/api/runs/{run_id}/impact/recompute", json={"supplement": {"passages": [
        {"version": "V3", "anchor": "A-06", "op": "delete"},
        {"version": "V3", "anchor": "A-07", "op": "delete"},
    ]}})
    withdrawn = client.get(f"/api/runs/{run_id}/impact").json()
    row = next(entry for entry in withdrawn["entries"] if entry["outcome"] == "withdraw")
    assert row["served"] and row["action"] == "notice_withdraw"
    assert row["dispatched_verdict"] == "accepted" and row["new_verdict"] == "review"

    # 原始归档与送达台账均未丢失、未被改写。
    stored = client.get(f"/api/runs/{run_id}").json()
    assert stored["result"] == baseline["result"]
    ledger = client.app.state.archive.list_dispatches(run_id)
    assert len(ledger) == 6 and all(row["verdict"] for row in ledger)


def test_interrupted_recompute_restores_previous_register(client, version_bump, monkeypatch):
    baseline = archive_baseline(client, {"sample": "clean"})
    run_id = baseline["id"]
    settings.RULE_VERSION = "2.0.0"
    previous = client.post(f"/api/runs/{run_id}/impact/recompute").json()

    def fail_commit(_run_id, _revision):
        raise RuntimeError("storage interrupted")

    monkeypatch.setattr(service, "commit_hook", fail_commit)
    with pytest.raises(RuntimeError):
        service.rebuild_impact(client.app.state.archive, run_id)
    monkeypatch.setattr(service, "commit_hook", None)

    restored = client.get(f"/api/runs/{run_id}/impact").json()
    assert restored["revision"] == previous["revision"]
    assert restored["entries"] == previous["entries"]
    assert restored["summary"] == previous["summary"]


def test_new_opinion_is_supplement_not_duplicate(client, version_bump):
    baseline = archive_baseline(client, {"sample": "clean"})
    settings.RULE_VERSION = "2.0.0"
    register = client.post(f"/api/runs/{baseline['id']}/impact/recompute", json={"supplement": {
        "directory": [{"id": "P006", "name": "新人", "aliases": [], "contact": "p006@example.test"}],
        "passages": [{"version": "V3", "anchor": "A-20", "op": "upsert", "page": 15,
                      "speaker_id": "P006", "topic": "新议题", "position": "support", "text": "全新意见。"}],
        "decisions": [{"version": "V3", "anchor": "A-20", "result": "accepted"}],
    }}).json()
    created = [entry for entry in register["entries"] if entry["is_new"]]
    assert len(created) == 1 and created[0]["outcome"] == "supplement"
    assert register["summary"]["total"] == 7
    # 再跑一次仍为 7 条，不重复。
    again = client.post(f"/api/runs/{baseline['id']}/impact/recompute", json={"supplement": {
        "directory": [{"id": "P006", "name": "新人", "aliases": [], "contact": "p006@example.test"}],
        "passages": [{"version": "V3", "anchor": "A-20", "op": "upsert", "page": 15,
                      "speaker_id": "P006", "topic": "新议题", "position": "support", "text": "全新意见。"}],
        "decisions": [{"version": "V3", "anchor": "A-20", "result": "accepted"}],
    }}).json()
    assert again["summary"]["total"] == 7 and len({e["key"] for e in again["entries"]}) == 7


def test_supplement_validation_and_missing_run(client, version_bump):
    baseline = archive_baseline(client, {"sample": "clean"})
    settings.RULE_VERSION = "2.0.0"
    bad = client.post(f"/api/runs/{baseline['id']}/impact/recompute", json={"supplement": {"unknown": []}})
    assert bad.status_code == 422 and bad.json()["code"] == "SUPPLEMENT_TABLES"
    assert client.post("/api/runs/missing/impact/recompute").status_code == 404
    assert client.get("/api/runs/missing/impact").status_code == 404


def test_dispatch_unknown_entry_rejected(client, version_bump):
    baseline = archive_baseline(client, {"sample": "clean"})
    settings.RULE_VERSION = "2.0.0"
    response = client.post(f"/api/runs/{baseline['id']}/impact/dispatch", json={"opinion_ids": ["nope"]})
    assert response.status_code == 404 and response.json()["code"] == "DISPATCH_UNKNOWN"


def test_impact_page_renders_book(client, version_bump):
    baseline = archive_baseline(client, {"sample": "clean"})
    settings.RULE_VERSION = "2.0.0"
    page = client.get(f"/work/impact?sample=clean&run={baseline['id']}")
    assert page.status_code == 200 and "旧案卷影响册" in page.text and "尚未重算" in page.text
    client.post(f"/api/runs/{baseline['id']}/impact/recompute")
    rendered = client.get(f"/work/impact?sample=clean&run={baseline['id']}").text
    assert "维持" in rendered and baseline["id"][:12] in rendered


def test_dirty_sample_with_none_pages_and_held_recipient(client, version_bump):
    """脏样例含删段（current_page 为 None），指纹排序不得报错；无效地址收件人暂缓。"""
    baseline = archive_baseline(client, {"sample": "dirty"})
    settings.RULE_VERSION = "2.0.0"
    register = client.post(f"/api/runs/{baseline['id']}/impact/recompute").json()
    assert {entry["key"] for entry in register["entries"]} and register["summary"]["maintain"] >= 1
    register = client.post(f"/api/runs/{baseline['id']}/impact/recompute", json={"supplement": {
        "passages": [
            {"version": "V3", "anchor": "A-06", "op": "delete"},
            {"version": "V3", "anchor": "A-07", "op": "delete"},
        ],
    }}).json()
    entry = next(row for row in register["entries"] if row["topic"] == "雨棚")
    assert entry["outcome"] == "withdraw" and entry["served"] is False
    target = next(row for row in register["recipients"] if row["speaker_id"] == "P005")
    assert target["state"] == "held" and target["actions"] == ["withdraw"]


def test_concurrent_recompute_keeps_single_book(client, version_bump):
    baseline = archive_baseline(client, {"sample": "clean"})
    settings.RULE_VERSION = "2.0.0"
    store = client.app.state.archive
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: service.rebuild_impact(store, baseline["id"]), range(8)))
    assert len({row["revision"] for row in outcomes}) == 8  # 串行提交，版本号不撞
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM impacts").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
    final = store.get_impact(baseline["id"])
    assert len({entry["key"] for entry in final["entries"]}) == len(final["entries"]) == 6
