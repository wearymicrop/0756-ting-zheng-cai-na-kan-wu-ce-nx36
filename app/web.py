from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.contract import HOME, STAGES
from app.errors import InputError
from app.manifest import sha256
from app.pipeline import calculate
from app.runs import archive_run
from app.samples import SAMPLE_NAMES, load_sample
from app.settings import ROOT, RULE_VERSION, TITLE

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(ROOT / "app/templates"))
templates.env.autoescape = True


@router.get("/work/impact")
def impact_book(request: Request, sample: str = "clean", run: str | None = None):
    """旧案卷影响册：默认把当前样例归档为旧版基线，再展示重算结果。"""
    titles = {name: caption for name, caption, _, _ in STAGES}
    store = request.app.state.archive
    baseline_id = run
    if baseline_id is None:
        baseline = archive_run(store, load_sample(sample), sample)
        baseline_id = baseline["id"]
    baseline = store.get(baseline_id)
    impact = store.get_impact(baseline_id)
    data = load_sample(sample)
    result = calculate(data)
    return templates.TemplateResponse(request=request, name="workbench.html", context={
        "project": TITLE, "titles": titles, "stage": "impact", "sample": sample,
        "samples": SAMPLE_NAMES, "result": result, "current": result[HOME],
        "rule_version": RULE_VERSION, "input_ref": sha256(data)[:10],
        "impact": impact, "baseline_id": baseline_id, "baseline": baseline,
        "dispatches": store.list_dispatches(baseline_id),
    })


@router.get("/")
@router.get("/work/{stage}")
def workbench(request: Request, stage: str = HOME, sample: str = "clean"):
    titles = {name: caption for name, caption, _, _ in STAGES}
    if stage not in titles:
        raise InputError("UNKNOWN_STAGE", "找不到该业务页面", 404)
    data = load_sample(sample)
    result = calculate(data)
    return templates.TemplateResponse(request=request, name="workbench.html", context={
        "project": TITLE, "titles": titles, "stage": stage, "sample": sample,
        "samples": SAMPLE_NAMES, "result": result, "current": result[stage],
        "rule_version": RULE_VERSION, "input_ref": sha256(data)[:10],
    })
