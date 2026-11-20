import re
from collections import defaultdict

from app.evidence import issue

ADDRESS = re.compile(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+")


def run(_data, previous):
    people = previous["speakers"]["people"]
    anchors = {row["anchor"]: row for row in previous["revisions"]["anchors"]}
    grouped, issues = defaultdict(list), []
    for opinion in previous["adoption"]["items"]:
        corrections = []
        for name in opinion["anchors"]:
            record = anchors[name]
            original = next((row for row in record["history"] if row["op"] == "upsert" and row["state"] == "active"), None)
            if original is None:
                continue
            for leaf in record["leaves"]:
                if leaf["page"] != original["page"] or record["status"] != "stable":
                    corrections.append({"anchor": name, "original_page": original["page"], "current_page": leaf["page"],
                                        "version": leaf["version"], "state": leaf["state"],
                                        "sources": [original["sources"][0], *([leaf["source"]] if "source" in leaf else [])]})
        grouped[opinion["speaker_id"]].append({"opinion_id": opinion["id"], "topic": opinion["topic"],
                                              "verdict": opinion["verdict"], "corrections": corrections})
    drafts = []
    for identifier, items in sorted(grouped.items()):
        person = people[identifier]
        address = person["contact"]
        valid = bool(address and ADDRESS.fullmatch(address))
        if not valid:
            issues.append(issue("CONTACT_MISSING", person["source"]))
        state = "ready" if valid and all(item["verdict"] != "review" for item in items) else "held"
        drafts.append({"id": identifier, "speaker": person["name"], "address": address, "state": state,
                       "items": items, "source": person["source"]})
    total = len(drafts)
    ready = sum(row["state"] == "ready" for row in drafts)
    return {"drafts": drafts, "ready": ready, "held": total - ready,
            "corrections": sum(len(item["corrections"]) for row in drafts for item in row["items"]), "issues": issues}
