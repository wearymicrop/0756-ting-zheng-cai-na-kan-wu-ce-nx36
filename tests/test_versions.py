from app.pipeline import calculate


def test_topological_order(clean):
    assert [v["version"] for v in clean["versions"]["versions"]] == ["V1","V2","V3"]


def test_cycle_isolated(dirty):
    """TRAP-20：脏样例中 V-X 与 V-Y 相互引用。"""
    error = dirty["versions"]["issues"][0]
    assert error["code"] == "VERSION_CYCLE"
    assert {s["raw"]["version"] for s in error["sources"]} == {"V-X","V-Y"}


def test_timestamps_by_instant(clean_data):
    """TRAP-11：干净样例将后版改为等价 UTC 时间。"""
    clean_data["versions"][1]["published_at"] = "2026-10-19T02:00:00Z"
    assert calculate(clean_data)["versions"]["versions"][1]["published_at"] == "2026-10-19T02:00:00+00:00"


def test_out_of_order_versions(clean_data):
    """TRAP-13：干净样例模拟后版先到。"""
    clean_data["versions"].reverse()
    assert calculate(clean_data)["versions"]["tips"] == ["V3"]


def test_missing_parent(clean_data):
    """TRAP-21：干净样例将末版指向缺失的前版。"""
    clean_data["versions"][-1]["parent"] = "V0"
    result = calculate(clean_data)["versions"]
    assert result["tips"] == ["V2"] and result["issues"][0]["code"] == "VERSION_ORPHAN"


def test_fork_tips(dirty):
    assert dirty["versions"]["tips"] == ["V3","V3-B"] and dirty["versions"]["forked"]
