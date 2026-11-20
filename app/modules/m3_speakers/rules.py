import unicodedata
from collections import defaultdict

from app.evidence import issue, key, rows


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", key(text)).casefold().split())


def directory(data):
    grouped, issues = defaultdict(list), []
    for raw, source in rows(data, "directory"):
        try:
            grouped[key(raw["id"])].append(source)
        except (KeyError, ValueError):
            issues.append(issue("BAD_DIRECTORY", source))
    people, aliases = {}, defaultdict(set)
    for person, sources in sorted(grouped.items()):
        if len(sources) > 1:
            issues.append(issue("SPEAKER_CONFLICT", *sources))
            continue
        source = sources[0]
        raw = source["raw"]
        try:
            name = key(raw["name"])
            names = raw.get("aliases", [])
            contact = raw.get("contact")
            if not isinstance(names, list) or (contact is not None and not isinstance(contact, str)):
                raise ValueError
            accepted = {normalized(value) for value in [name, *names]}
        except (KeyError, ValueError):
            issues.append(issue("BAD_DIRECTORY", source))
            continue
        for alias in accepted:
            aliases[alias].add(person)
        people[person] = {"id": person, "name": name, "contact": contact, "source": source}
    return people, aliases, issues


def identify(raw, people, aliases):
    identifier, name = raw.get("speaker_id"), raw.get("speaker")
    try:
        if identifier is not None:
            identifier = key(identifier)
            if identifier in people and (name is None or identifier in aliases.get(normalized(name), set())):
                return identifier, None
        elif name is not None:
            candidates = aliases.get(normalized(name), set())
            if len(candidates) == 1:
                return next(iter(candidates)), None
            if candidates:
                return None, "AMBIGUOUS_NAME"
    except ValueError:
        pass
    return None, "SPEAKER_UNKNOWN"


def run(data, previous):
    people, aliases, issues = directory(data)
    opinions, rejected = [], []
    for op in previous["anchors"]["operations"]:
        if op["op"] != "upsert":
            continue
        source = op["sources"][0]
        raw = source["raw"]
        person, problem = identify(raw, people, aliases)
        if problem:
            candidates = sorted(aliases.get(normalized(raw["speaker"]), set())) if problem == "AMBIGUOUS_NAME" else []
            issues.append(issue(problem, source, *(people[person_id]["source"] for person_id in candidates)))
            rejected.append(source["line"])
            continue
        try:
            topic = normalized(raw["topic"])
            position = raw["position"]
            text = key(raw["text"])
            if position not in ("support", "oppose", "amend"):
                raise ValueError
        except (KeyError, ValueError):
            issues.append(issue("BAD_OPINION", source))
            rejected.append(source["line"])
            continue
        opinions.append({"line": source["line"], "speaker_id": person, "speaker": people[person]["name"],
                         "topic": topic, "position": position, "text": text, "source": source})
    return {"people": people, "identified": opinions, "rejected_lines": rejected, "issues": issues}
