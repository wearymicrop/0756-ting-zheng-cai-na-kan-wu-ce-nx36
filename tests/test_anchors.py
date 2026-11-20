from app.pipeline import calculate


def test_stable_operation_key(clean):
    row = next(r for r in clean["anchors"]["operations"] if r["version"]=="V3" and r["anchor"]=="A-01")
    assert (row["page"],row["op"],row["sources"][0]["line"]) == (11,"move",13)


def test_duplicate_anchor_quarantined(dirty):
    """TRAP-14：脏样例同一版本同锚点两道移页。"""
    issue = next(i for i in dirty["anchors"]["issues"] if i["code"]=="ANCHOR_CONFLICT")
    assert [s["raw"]["page"] for s in issue["sources"]] == [9,12]


def test_removed_passage_no_page(dirty):
    row = next(r for r in dirty["anchors"]["operations"] if r["op"]=="delete")
    assert row["anchor"] == "A-08" and row["page"] is None


def test_page_out_of_range(clean_data):
    clean_data["passages"][0]["page"] = 13
    assert calculate(clean_data)["anchors"]["issues"][0]["code"] == "PAGE_INVALID"


def test_unavailable_revision(dirty):
    assert any(i["code"] == "VERSION_UNAVAILABLE" and i["sources"][0]["line"]==24 for i in dirty["anchors"]["issues"])


def test_movement_keeps_line(clean):
    assert clean["anchors"]["rejected_lines"] == []
    assert clean["anchors"]["input_rows"] == 16
