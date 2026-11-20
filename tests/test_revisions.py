from app.pipeline import calculate


def test_renumbering_preserves_text_origin(clean):
    leaf = clean["revisions"]["anchors"][0]["leaves"][0]
    assert (leaf["page"], leaf["origin"]["line"], leaf["source"]["line"]) == (11,1,13)


def test_parallel_deletion_visible(dirty):
    anchor = next(r for r in dirty["revisions"]["anchors"] if r["anchor"]=="A-08")
    assert anchor["status"] == "fork"
    assert [r["state"] for r in anchor["leaves"]] == ["active","deleted"]


def test_both_branches_same_page(dirty):
    anchor = dirty["revisions"]["anchors"][0]
    assert anchor["status"] == "stable" and [r["page"] for r in anchor["leaves"]] == [11,11]


def test_unknown_move_is_invalid(dirty):
    assert any(i["code"]=="ANCHOR_MISSING" and i["sources"][0]["raw"]["anchor"]=="A-10" for i in dirty["revisions"]["issues"])


def test_version_shrinks_pages(clean_data):
    clean_data["versions"][-1]["pages"] = 5
    assert any(i["code"]=="PAGE_INVALID" for i in calculate(clean_data)["revisions"]["issues"])


def test_content_revision_resets_origin(clean):
    leaf = next(r for r in clean["revisions"]["anchors"] if r["anchor"]=="A-05")["leaves"][0]
    assert leaf["origin"]["line"] == 16 and leaf["content_version"] == "V2"
