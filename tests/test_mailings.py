from app.pipeline import calculate


def test_clean_envelopes(clean):
    assert (clean["mailings"]["ready"],clean["mailings"]["held"]) == (5,0)


def test_dirty_envelopes(dirty):
    assert (dirty["mailings"]["ready"],dirty["mailings"]["held"]) == (2,3)


def test_missing_address_holds(dirty):
    """TRAP-07：脏样例联系地址为占位符。"""
    assert [s["raw"]["contact"] for i in dirty["mailings"]["issues"] for s in i["sources"]] == ["—"]
    assert next(r for r in dirty["mailings"]["drafts"] if r["id"]=="P005")["state"] == "held"


def test_correction_has_original_and_final_page(clean):
    draft = clean["mailings"]["drafts"][0]
    row = draft["items"][0]["corrections"][0]
    assert (row["original_page"],row["current_page"]) == (3,11)
    assert [s["line"] for s in row["sources"]] == [1,13]


def test_same_person_combines_topics(clean):
    assert {x["topic"] for x in clean["mailings"]["drafts"][0]["items"]} == {"慢行入口","绿带"}


def test_no_draft_without_identified_opinions(clean_data):
    clean_data["directory"] = []
    assert calculate(clean_data)["mailings"]["drafts"] == []
