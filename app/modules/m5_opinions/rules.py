from collections import defaultdict

from app.evidence import issue
from app.manifest import sha256


def run(_data, previous):
    known = {row["line"]: row for row in previous["speakers"]["identified"]}
    grouped, issues = defaultdict(list), []
    for anchor in previous["revisions"]["anchors"]:
        sources = [source for row in anchor["history"] for source in row["sources"]]
        recognized = [known[s["line"]] for s in sources if s["line"] in known]
        subjects = {(row["speaker_id"], row["topic"], row["position"]) for row in recognized}
        if len(subjects) > 1:
            issues.append(issue("ANCHOR_CHANGED", *(row["source"] for row in recognized)))
            continue
        if len(subjects) == 1:
            grouped[next(iter(subjects))].append((anchor, sources, recognized))
    items, attributed_lines = [], set()
    rejected = set(previous["anchors"]["rejected_lines"] + previous["speakers"]["rejected_lines"])
    for subject, entries in sorted(grouped.items()):
        person, topic, position = subject
        anchors = [entry[0] for entry in entries]
        sources = sorted((src for _, evidence, _ in entries for src in evidence), key=lambda src: src["line"])
        recognized = [row for _, _, people in entries for row in people]
        active = [leaf for anchor in anchors for leaf in anchor["leaves"] if leaf["state"] == "active"]
        primary = min((leaf["origin"]["line"] for leaf in active), default=min(row["line"] for row in recognized))
        ready = all(anchor["status"] == "stable" for anchor in anchors) and not rejected.intersection(s["line"] for s in sources)
        attributed_lines.update(src["line"] for src in sources)
        items.append({"id": sha256(subject)[:16], "speaker_id": person, "speaker": recognized[0]["speaker"],
                      "topic": topic, "position": position, "anchors": [row["anchor"] for row in anchors],
                      "primary_line": primary, "sources": sources, "state": "stable" if ready else "review"})
    unassigned = sorted(set(range(1, previous["anchors"]["input_rows"] + 1)) - attributed_lines)
    return {"items": items, "unassigned_lines": unassigned, "issues": issues}
