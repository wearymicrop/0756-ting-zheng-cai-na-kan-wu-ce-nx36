from collections import defaultdict

from app.evidence import issue, key, rows


def run(data, previous):
    versions = {record["version"]: record for record in previous["versions"]["versions"]}
    groups, issues, rejected = defaultdict(list), [], []
    for raw, source in rows(data, "passages"):
        try:
            anchor, version = key(raw["anchor"]), key(raw["version"])
        except (KeyError, ValueError):
            issues.append(issue("BAD_PASSAGE", source))
            rejected.append(source["line"])
            continue
        if version not in versions:
            issues.append(issue("VERSION_UNAVAILABLE", source))
            rejected.append(source["line"])
            continue
        groups[version, anchor].append(source)
    operations = []
    for (version, anchor), sources in sorted(groups.items()):
        base = {"anchor": anchor, "version": version, "sources": sources}
        code = None
        raw = sources[0]["raw"]
        op, page = raw.get("op"), raw.get("page")
        if len(sources) > 1:
            code = "ANCHOR_CONFLICT"
        elif op not in ("upsert", "move", "delete") or (op == "delete" and page is not None):
            code = "BAD_PASSAGE"
        elif op in ("upsert", "move") and (type(page) is not int or not 1 <= page <= versions[version]["pages"]):
            code = "PAGE_INVALID"
        if code:
            issues.append(issue(code, *sources))
            rejected.extend(s["line"] for s in sources)
            operations.append({**base, "op": "invalid", "page": None})
        else:
            operations.append({**base, "op": op, "page": page})
    return {"operations": operations, "rejected_lines": sorted(rejected), "input_rows": len(data["passages"]), "issues": issues}
