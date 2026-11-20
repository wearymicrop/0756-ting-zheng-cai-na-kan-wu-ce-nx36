from collections import defaultdict

from app.evidence import issue


def fingerprint(state):
    if state["state"] == "active":
        return ("active", state["page"], state["speaker_id"], state["topic"], state["position"], state["text"])
    return (state["state"],)


def apply(op, before, recognized, issues):
    source = op["sources"][0]
    kind = op["op"]
    invalid = {"state": "invalid", "page": None, "source": source}
    if kind == "invalid":
        return invalid
    if kind == "upsert":
        known = recognized.get(source["line"])
        return {**known, "state": "active", "page": op["page"], "source": source,
                "origin": source, "content_version": op["version"]} if known else invalid
    if before is None or before["state"] != "active":
        issues.append(issue("ANCHOR_MISSING", source))
        return invalid
    if kind == "delete":
        return {"state": "deleted", "page": None, "old_page": before["page"], "source": source, "origin": before["origin"]}
    return {**before, "page": op["page"], "source": source}


def run(_data, previous):
    registry = previous["versions"]
    recognized = {entry["line"]: entry for entry in previous["speakers"]["identified"]}
    ops = defaultdict(dict)
    for row in previous["anchors"]["operations"]:
        ops[row["anchor"]][row["version"]] = row
    anchors, issues = [], []
    for anchor, operations in sorted(ops.items()):
        snapshot, history = {}, []
        for v in registry["versions"]:
            name = v["version"]
            previous_state = snapshot.get(v["parent"])
            operation = operations.get(name)
            state = apply(operation, previous_state, recognized, issues) if operation else previous_state
            if state is not None and state["state"] == "active" and state["page"] > v["pages"]:
                issues.append(issue("PAGE_INVALID", state["source"], v["source"]))
                state = {"state": "invalid", "page": None, "source": state["source"]}
            snapshot[name] = state
            if operation:
                history.append({**operation, "state": state["state"]})
        leaves = [{"version": name, **(snapshot[name] or {"state": "absent", "page": None})} for name in registry["tips"]]
        distinct = {fingerprint(state) for state in leaves}
        if len(distinct) > 1:
            status, code = "fork", "REVISION_FORK"
        elif leaves and leaves[0]["state"] == "active":
            status, code = "stable", None
        elif leaves and leaves[0]["state"] == "deleted":
            status, code = "deleted", "ANCHOR_DELETED"
        else:
            status, code = "unresolved", "ANCHOR_UNRESOLVED"
        if code:
            issues.append(issue(code, *(leaf["source"] for leaf in leaves if "source" in leaf)))
        active = [name for name, state in snapshot.items() if state and state["state"] == "active"]
        anchors.append({"anchor": anchor, "status": status, "leaves": leaves, "history": history, "active_versions": active})
    return {"anchors": anchors, "tips": registry["tips"], "issues": issues}
