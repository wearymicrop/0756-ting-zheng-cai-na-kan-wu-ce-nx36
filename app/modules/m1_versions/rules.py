from collections import defaultdict, deque

from app.errors import InputError
from app.evidence import issue, key, rows, timestamp


def read_versions(data):
    groups, issues = defaultdict(list), []
    for raw, source in rows(data, "versions"):
        try:
            groups[key(raw["version"])].append(source)
        except (KeyError, ValueError):
            issues.append(issue("BAD_VERSION", source))
    records = {}
    for version, sources in sorted(groups.items()):
        if len(sources) != 1:
            issues.append(issue("DUPLICATE_VERSION", *sources))
            continue
        source = sources[0]
        raw = source["raw"]
        try:
            parent = None if raw["parent"] is None else key(raw["parent"])
            published = timestamp(raw["published_at"])
            pages = raw["pages"]
            if type(pages) is not int or not 1 <= pages <= 10000:
                raise ValueError
        except (KeyError, ValueError, OverflowError):
            issues.append(issue("BAD_VERSION", source))
            continue
        records[version] = {"version": version, "parent": parent, "published_at": published.isoformat(),
                            "pages": pages, "source": source}
    return records, issues


def unresolved_versions(records, valid, issues):
    known = set(valid)
    for version in records:
        if version in known:
            continue
        chain, seen = [], set()
        head = version
        while head in records and head not in known and head not in seen:
            seen.add(head)
            chain.append(head)
            head = records[head]["parent"]
        if head in seen:
            cycle = chain[chain.index(head):]
            issues.append(issue("VERSION_CYCLE", *(records[node]["source"] for node in cycle)))
            known.update(cycle)
        for node in chain:
            if node not in known:
                issues.append(issue("VERSION_ORPHAN", records[node]["source"]))
                known.add(node)


def run(data, _previous):
    try:
        root = key(data["config"]["root"])
        docket = key(data["config"]["docket"])
    except (KeyError, ValueError) as error:
        raise InputError("BAD_DOCKET", "案号或首版标识有误") from error
    if len(data["versions"]) > 128:
        raise InputError("VERSION_LIMIT", "单案文书版本最多 128 条")
    records, issues = read_versions(data)
    children = defaultdict(list)
    for record in records.values():
        children[record["parent"]].append(record["version"])
    queue = deque([root] if root in records and records[root]["parent"] is None else [])
    valid, rejected, accepted_parents = {}, set(), set()
    while queue:
        name = queue.popleft()
        node = records[name]
        parent = node["parent"]
        if parent is not None:
            if timestamp(node["published_at"]) <= timestamp(valid[parent]["published_at"]):
                issues.append(issue("VERSION_ORDER", valid[parent]["source"], node["source"]))
                rejected.add(name)
                continue
            accepted_parents.add(parent)
        valid[name] = node
        queue.extend(children[name])
    unresolved_versions(records, set(valid) | rejected, issues)
    tips = sorted(valid.keys() - accepted_parents)
    return {"docket": docket, "root": root, "versions": list(valid.values()), "tips": tips,
            "forked": len(tips) > 1, "issues": issues}
