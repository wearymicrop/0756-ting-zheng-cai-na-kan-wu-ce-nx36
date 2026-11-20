"""旧案卷影响册规则。

归档保存的是旧规则下的不可变快照；当前规则重算后，本模块把两次寄送草案按
意见稳定键逐行对齐，给出每条旧勘误的「维持 / 追补 / 撤回」结论。

- 稳定键取意见主行的 opinion_id（由登记号、议题、立场哈希而来），
  页码、末版内容或采纳结论变化都不会改变键，跨版本可对齐。
- 已送达条目只允许追加补寄/撤回单，原结论由寄送台账冻结，不在此处改写。
"""
from app.errors import InputError
from app.manifest import rule_version
from app.modules.m7_mailings.rules import ADDRESS
from app.reasons import REASONS, STATUS_LABELS

MAINTAIN, SUPPLEMENT, WITHDRAW = "maintain", "supplement", "withdraw"


def flatten_mailings(result):
    """把按收件人归并的寄送草案展平为以意见为单位的勘误条目。"""
    entries = {}
    for draft in result["mailings"]["drafts"]:
        for item in draft["items"]:
            entries[item["opinion_id"]] = {
                "opinion_id": item["opinion_id"],
                "speaker_id": draft["id"],
                "speaker": draft["speaker"],
                "address": draft["address"],
                "draft_state": draft["state"],
                "topic": item["topic"],
                "verdict": item["verdict"],
                "corrections": item["corrections"],
            }
    return entries


def page_signature(corrections):
    """页码勘误的可比对指纹：锚点、原页、现页、末版与状态。"""
    # current_page 在删段时为 None，不能与整数直接比较，按字符串化后的元组排序。
    return sorted(
        ((c["anchor"], c["original_page"], c["current_page"], c["version"], c["state"]) for c in corrections),
        key=lambda row: tuple("" if part is None else str(part) for part in row),
    )


def mailable(address, draft_state):
    return bool(address and ADDRESS.fullmatch(address)) and draft_state == "ready"


def merge_supplement(base, supplement):
    """合并下午补交件：只允许追加原有输入表或更新批次设置，不改动旧行。"""
    from app.contract import TABLES

    if not isinstance(supplement, dict) or not supplement or any(
        key not in TABLES and key != "config" for key in supplement
    ):
        raise InputError("SUPPLEMENT_TABLES", "补交数据只能覆盖原有输入表或批次设置")
    merged = {key: (dict(rows) if key == "config" else list(rows)) for key, rows in base.items()}
    for key, value in supplement.items():
        if key == "config":
            if not isinstance(value, dict):
                raise InputError("SUPPLEMENT_TABLES", "补交的批次设置有误")
            merged["config"] = {**base["config"], **value}
        else:
            if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
                raise InputError("SUPPLEMENT_TABLES", f"补交的 {key} 行格式有误")
            merged[key] = [*base[key], *value]
    return merged


def _recipient(side):
    address = side["address"]
    valid = bool(address and ADDRESS.fullmatch(address))
    return {
        "speaker_id": side["speaker_id"],
        "speaker": side["speaker"],
        "address": address,
        "valid_address": valid,
        "state": side["draft_state"],
        "mailable": mailable(address, side["draft_state"]),
    }


def _entry(key, old, new, served, baseline_id):
    """生成单条影响册行；old/new 至少有一个非空。"""
    changed = []
    if old is None:
        outcome, reason = SUPPLEMENT, "IMPACT_SUPPLEMENT"
        changed.append("entry")
        recipient = _recipient(new)
        old_verdict, new_verdict = None, new["verdict"]
        old_pages, new_pages = [], page_signature(new["corrections"])
    elif new is None:
        outcome, reason = WITHDRAW, "IMPACT_WITHDRAW"
        changed.append("entry")
        recipient = _recipient(old)
        old_verdict, new_verdict = old["verdict"], None
        old_pages, new_pages = page_signature(old["corrections"]), []
    else:
        old_verdict, new_verdict = old["verdict"], new["verdict"]
        old_pages, new_pages = page_signature(old["corrections"]), page_signature(new["corrections"])
        if old_verdict != new_verdict:
            changed.append("verdict")
        if old_pages != new_pages:
            changed.append("pages")
        # 旧勘误结论确定，重算后锚点删除或落入待审（review），原勘误无法维持 -> 撤回；
        # 仍能定论的结论/页码变化才向同一收件人追补更正单。
        if changed and old_verdict != "review" and new_verdict == "review":
            outcome, reason = WITHDRAW, "IMPACT_WITHDRAW"
            recipient = _recipient(old)
        elif changed:
            outcome, reason = SUPPLEMENT, "IMPACT_SUPPLEMENT"
            recipient = _recipient(new)
        else:
            outcome, reason = MAINTAIN, "IMPACT_MAINTAIN"
            recipient = _recipient(new)
    dispatch = served.get((baseline_id, key))
    action = "none"
    if dispatch is not None and outcome == SUPPLEMENT:
        action = "notice_supplement"
    elif dispatch is not None and outcome == WITHDRAW:
        action = "notice_withdraw"
    return {
        "key": key,
        "topic": (new or old)["topic"],
        "outcome": outcome,
        "outcome_label": STATUS_LABELS[outcome],
        "reason_code": reason,
        "reason_label": REASONS[reason],
        "changed_fields": changed,
        "is_new": old is None,
        "served": dispatch is not None,
        "dispatched_verdict": dispatch["verdict"] if dispatch else None,
        "served_locked": dispatch is not None and outcome != MAINTAIN,
        "action": action,
        "old_verdict": old_verdict,
        "new_verdict": new_verdict,
        "old_pages": old_pages,
        "new_pages": new_pages,
        "recipient": recipient,
        "old_corrections": [] if old is None else old["corrections"],
        "new_corrections": [] if new is None else new["corrections"],
    }


def _recipients(entries):
    """汇总待补寄/撤回对象：只收需要动作的条目，按收件人归并。"""
    grouped = {}
    for entry in entries:
        if entry["outcome"] == MAINTAIN:
            continue
        person = entry["recipient"]
        bucket = grouped.setdefault(person["speaker_id"], {
            "speaker_id": person["speaker_id"], "speaker": person["speaker"],
            "address": person["address"], "mailable": True, "actions": set(), "entries": [],
        })
        bucket["actions"].add(entry["outcome"])
        bucket["entries"].append(entry["key"])
        if not person["mailable"]:
            bucket["mailable"] = False
    recipients = []
    for bucket in sorted(grouped.values(), key=lambda row: row["speaker_id"]):
        bucket["actions"] = sorted(bucket["actions"])
        bucket["state"] = "ready" if bucket["mailable"] else "held"
        recipients.append(bucket)
    return recipients


def build_register(baseline, new_result, dispatches):
    """比对旧归档与当前规则结果，dispatches 为只追加的已送达台账行。"""
    baseline_id = baseline["id"]
    old_entries = flatten_mailings(baseline["result"])
    new_entries = flatten_mailings(new_result)
    served = {(row["run_id"], row["opinion_id"]): row for row in dispatches}
    keys = sorted(set(old_entries) | set(new_entries))
    entries = [
        _entry(key, old_entries.get(key), new_entries.get(key), served, baseline_id) for key in keys
    ]
    summary = {
        "total": len(entries),
        "maintain": sum(row["outcome"] == MAINTAIN for row in entries),
        "supplement": sum(row["outcome"] == SUPPLEMENT for row in entries),
        "withdraw": sum(row["outcome"] == WITHDRAW for row in entries),
        "served": sum(row["served"] for row in entries),
        "pending": sum(not row["served"] for row in entries),
        "changed": any(row["outcome"] != MAINTAIN for row in entries),
    }
    return {
        "baseline_id": baseline_id,
        "baseline_rule_version": baseline["manifest"]["rule_version"],
        "current_rule_version": rule_version(),
        "summary": summary,
        "entries": entries,
        "recipients": _recipients(entries),
        "dispatches": list(dispatches),
    }
