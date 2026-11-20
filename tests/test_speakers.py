from app.pipeline import calculate


def test_same_named_distinct_people(clean):
    people = clean["speakers"]["people"]
    assert people["P002"]["name"] == people["P003"]["name"] == "周岚"
    assert [r["speaker_id"] for r in clean["speakers"]["identified"] if r["speaker"] == "周岚"] == ["P002","P003"]


def test_alias_resolution(clean_data):
    """TRAP-22：干净样例改用登记别名并加空白。"""
    clean_data["passages"][0].pop("speaker_id")
    clean_data["passages"][0]["speaker"] = "  林先生　"
    assert calculate(clean_data)["speakers"]["identified"][0]["speaker_id"] == "P001"


def test_ambiguous_name_candidates(dirty):
    error = dirty["speakers"]["issues"][0]
    assert error["code"] == "AMBIGUOUS_NAME"
    assert [s["raw"]["id"] for s in error["sources"][1:]] == ["P002", "P003"]


def test_mismatched_explicit_identity(clean_data):
    clean_data["passages"][0]["speaker"] = "宋禾"
    assert calculate(clean_data)["speakers"]["issues"][0]["code"] == "SPEAKER_UNKNOWN"


def test_duplicate_directory_number(clean_data):
    clean_data["directory"].append({**clean_data["directory"][0],"name":"其他人"})
    assert calculate(clean_data)["speakers"]["issues"][0]["code"] == "SPEAKER_CONFLICT"


def test_recognition_by_unique_name(clean):
    assert next(r for r in clean["speakers"]["identified"] if r["line"]==16)["speaker_id"] == "P004"
