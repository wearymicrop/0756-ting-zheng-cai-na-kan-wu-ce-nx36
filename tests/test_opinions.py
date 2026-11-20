from app.pipeline import calculate


def test_paraphrases_keep_sources(clean):
    item = next(r for r in clean["opinions"]["items"] if r["topic"]=="慢行入口")
    assert item["anchors"] == ["A-01","A-02"]
    assert [s["line"] for s in item["sources"]] == [1,2,9,10,13]


def test_same_name_not_merged(clean):
    assert {r["speaker_id"] for r in clean["opinions"]["items"] if r["topic"]=="夜间照明"} == {"P002","P003"}


def test_different_position_not_merged(clean_data):
    clean_data["passages"][1]["position"] = "oppose"
    assert {r["position"] for r in calculate(clean_data)["opinions"]["items"] if r["topic"]=="慢行入口"} == {"oppose","amend"}


def test_latest_primary_source(clean):
    assert next(r for r in clean["opinions"]["items"] if r["topic"]=="排水沟")["primary_line"] == 16


def test_unassigned_rows_retained(dirty):
    assert dirty["opinions"]["unassigned_lines"] == [20,21,24]


def test_anchor_cannot_switch_speaker_silently(clean_data):
    clean_data["passages"][15].update(speaker_id="P005",speaker="何岱")
    section = calculate(clean_data)["opinions"]
    assert section["issues"][0]["code"] == "ANCHOR_CHANGED"
    assert {5,16} <= set(section["unassigned_lines"])
