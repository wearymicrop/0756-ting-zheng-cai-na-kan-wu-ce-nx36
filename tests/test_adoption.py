from app.pipeline import calculate


def test_clean_coverage(clean):
    assert clean["adoption"]["totals"] == dict(input=16,effective=6,repetition=10,disputed=0,difference=0)


def test_dirty_coverage(dirty):
    assert dirty["adoption"]["totals"] == dict(input=24,effective=3,repetition=5,disputed=16,difference=0)
    assert sorted(r["line"] for r in dirty["adoption"]["coverage"]) == list(range(1,25))


def test_forked_decision_review(dirty):
    """TRAP-19：脏样例同一意见有相反的末版采纳结论。"""
    assert dirty["adoption"]["issues"][0]["code"] == "DECISION_FORK"
    item = next(r for r in dirty["adoption"]["items"] if r["topic"]=="慢行入口")
    assert item["verdict"] == "review"
    assert {r["result"] for r in item["decisions"]} == {"accepted","rejected"}


def test_moved_passage_inherits_decision(clean):
    item = next(r for r in clean["adoption"]["items"] if r["topic"]=="绿带")
    assert item["decisions"][0]["decision_version"] == "V1"


def test_changed_passage_requires_new_decision(clean_data):
    clean_data["decisions"].pop()
    item = next(r for r in calculate(clean_data)["adoption"]["items"] if r["topic"]=="排水沟")
    assert item["verdict"] == "review" and item["decisions"][0]["result"] is None


def test_same_revision_conflicting_decisions(clean_data):
    clean_data["decisions"].append({**clean_data["decisions"][0],"result":"rejected"})
    assert calculate(clean_data)["adoption"]["issues"][0]["code"] == "DECISION_CONFLICT"
