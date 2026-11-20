"""旧案卷影响册服务：把不可变归档、当前规则重算与只追加台账串起来。"""
from datetime import datetime, timezone

from app.errors import InputError
from app.modules.m8_impact.rules import build_register, merge_supplement
from app.pipeline import calculate

# 测试可替换以模拟“重算中断”：提交前抛错，整册事务必须回滚。
commit_hook = None


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rebuild_impact(store, run_id, supplement=None):
    """用当前规则重跑旧案卷并整册替换影响册；中断时保留旧版。"""
    baseline = store.get(run_id)
    data = merge_supplement(baseline["input"], supplement) if supplement else baseline["input"]
    new_result = calculate(data)
    register = build_register(baseline, new_result, store.list_dispatches(run_id))
    return store.replace_impact(run_id, register, _now(), before_commit=commit_hook)


def mark_dispatched(store, run_id, opinion_ids):
    """登记已送达勘误（先发）：只追加台账，原结论按送达时快照冻结。"""
    baseline = store.get(run_id)
    wanted = set(opinion_ids)
    available = {}
    for draft in baseline["result"]["mailings"]["drafts"]:
        if draft["state"] != "ready":
            continue
        for item in draft["items"]:
            available[item["opinion_id"]] = (draft, item)
    unknown = sorted(wanted - set(available))
    if unknown:
        raise InputError("DISPATCH_UNKNOWN", "条目不在该案卷可寄送清单内", 404)
    already = {row["opinion_id"] for row in store.list_dispatches(run_id)}
    stamp = _now()
    items = []
    for opinion_id in sorted(wanted):
        if opinion_id in already:
            continue
        draft, item = available[opinion_id]
        # 冻结送达时的结论与页码勘误，之后任何重算都不得改写。
        items.append({
            "run_id": run_id,
            "opinion_id": opinion_id,
            "topic": item["topic"],
            "speaker_id": draft["id"],
            "address": draft["address"],
            "verdict": item["verdict"],
            "corrections": item["corrections"],
            "dispatched_at": stamp,
        })
    dispatches = store.add_dispatches(run_id, items, stamp)
    return {
        "baseline_id": run_id,
        "newly_recorded": len(items),
        "already_served": len(wanted) - len(items),
        "total_served": len(dispatches),
        "dispatches": dispatches,
    }


def all_ready_ids(baseline):
    """旧案卷中当前可寄送（地址与结论均核实）的条目键。"""
    return [
        item["opinion_id"]
        for draft in baseline["result"]["mailings"]["drafts"] if draft["state"] == "ready"
        for item in draft["items"]
    ]
