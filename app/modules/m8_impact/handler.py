from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.errors import InputError
from app.modules.m8_impact import service

router = APIRouter(prefix="/api/runs/{run_id}/impact", tags=["旧案卷影响册"])


class RecomputeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplement: dict[str, Any] | None = None


class DispatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opinion_ids: list[str] = Field(default_factory=list)


@router.post("/recompute")
def recompute(run_id: str, request: Request, body: RecomputeBody | None = None):
    supplement = body.supplement if body is not None else None
    return service.rebuild_impact(request.app.state.archive, run_id, supplement)


@router.get("")
def read_impact(run_id: str, request: Request):
    register = request.app.state.archive.get_impact(run_id)
    if register is None:
        raise InputError("IMPACT_MISSING", "该案卷尚未在新规则下重算", 404)
    return register


@router.post("/dispatch")
def dispatch(run_id: str, request: Request, body: DispatchBody | None = None):
    store = request.app.state.archive
    baseline = store.get(run_id)
    opinion_ids = body.opinion_ids if body is not None and body.opinion_ids else service.all_ready_ids(baseline)
    if not opinion_ids:
        raise InputError("DISPATCH_EMPTY", "该案卷没有可寄送的勘误条目")
    result = service.mark_dispatched(store, run_id, opinion_ids)
    # 送达后立即重算影响册：已送达条目改走补寄/撤回单，待寄送对象随之更新。
    register = service.rebuild_impact(store, run_id)
    return {**result, "impact": register}
