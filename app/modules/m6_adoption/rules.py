from collections import Counter, defaultdict

from app.evidence import issue, key, rows


def decisions_for(data, versions, anchor_versions):
    groups, issues = defaultdict(list), []
    for raw, source in rows(data, "decisions"):
        try:
            version, anchor = key(raw["version"]), key(raw["anchor"])
        except (KeyError, ValueError):
            issues.append(issue("BAD_DECISION", source))
            continue
        if version not in versions or version not in anchor_versions.get(anchor, set()):
            issues.append(issue("DECISION_ANCHOR", source))
            continue
        groups[version, anchor].append(source)
    decisions = {}
    for subject, sources in sorted(groups.items()):
        result = sources[0]["raw"].get("result")
        if len(sources) > 1:
            issues.append(issue("DECISION_CONFLICT", *sources))
            result = None
        elif result not in ("accepted", "rejected", "partial"):
            issues.append(issue("BAD_DECISION", *sources))
            result = None
        decisions[subject] = {"result": result, "sources": sources}
    return decisions, issues


def applicable(leaf, anchor, versions, decisions):
    node = leaf["version"]
    if leaf["state"] == "active":
        while node is not None:
            decision = decisions.get((node, anchor))
            if decision:
                return {"anchor": anchor, "tip": leaf["version"], "decision_version": node, **decision}
            if node == leaf["content_version"]:
                break
            node = versions[node]["parent"]
    return {"anchor": anchor, "tip": leaf["version"], "decision_version": None, "result": None, "sources": []}


def run(data, previous):
    versions = {row["version"]: row for row in previous["versions"]["versions"]}
    anchors = {row["anchor"]: row for row in previous["revisions"]["anchors"]}
    anchor_versions = {name: set(anchor["active_versions"]) for name, anchor in anchors.items()}
    decisions, issues = decisions_for(data, versions, anchor_versions)
    aliases, items = {}, []
    for line in previous["opinions"]["unassigned_lines"]:
        aliases[line] = "disputed"
    for opinion in previous["opinions"]["items"]:
        matrix = [applicable(leaf, anchor, versions, decisions) for anchor in opinion["anchors"] for leaf in anchors[anchor]["leaves"]]
        conclusions = {cell["result"] for cell in matrix}
        certain = conclusions - {None}
        if len(certain) > 1:
            issues.append(issue("DECISION_FORK", *(src for cell in matrix for src in cell["sources"])))
        elif None in conclusions and opinion["state"] == "stable":
            issues.append(issue("DECISION_MISSING", *opinion["sources"]))
        verdict = next(iter(certain)) if len(certain) == 1 and None not in conclusions and opinion["state"] == "stable" else "review"
        for source in opinion["sources"]:
            line = source["line"]
            aliases[line] = "disputed" if verdict == "review" else "effective" if line == opinion["primary_line"] else "repetition"
        items.append({**opinion, "verdict": verdict, "decisions": matrix})
    coverage = [{"line": src["line"], "category": aliases[src["line"]], "source": src} for _, src in rows(data, "passages")]
    counts = Counter(row["category"] for row in coverage)
    totals = {"input": len(data["passages"]), **{key: counts[key] for key in ("effective", "repetition", "disputed")}}
    totals["difference"] = totals["input"] - sum(counts.values())
    return {"items": items, "coverage": coverage, "totals": totals,
            "status": "DIFFERENCE" if totals["difference"] else "REVIEW" if counts["disputed"] or issues else "MATCHED",
            "issues": issues}
