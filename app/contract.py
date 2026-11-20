from app.modules.m1_versions.handler import router as versions_router
from app.modules.m1_versions.rules import run as versions
from app.modules.m2_anchors.handler import router as anchors_router
from app.modules.m2_anchors.rules import run as anchors
from app.modules.m3_speakers.handler import router as speakers_router
from app.modules.m3_speakers.rules import run as speakers
from app.modules.m4_revisions.handler import router as revisions_router
from app.modules.m4_revisions.rules import run as revisions
from app.modules.m5_opinions.handler import router as opinions_router
from app.modules.m5_opinions.rules import run as opinions
from app.modules.m6_adoption.handler import router as adoption_router
from app.modules.m6_adoption.rules import run as adoption
from app.modules.m7_mailings.handler import router as mailings_router
from app.modules.m7_mailings.rules import run as mailings

TABLES = ("versions", "passages", "directory", "decisions")
HOME = "revisions"
STAGES = (
    ("versions", "文书版本", versions, versions_router),
    ("anchors", "页码锚点", anchors, anchors_router),
    ("speakers", "发言识别", speakers, speakers_router),
    ("revisions", "修订链路", revisions, revisions_router),
    ("opinions", "意见归并", opinions, opinions_router),
    ("adoption", "采纳核对", adoption, adoption_router),
    ("mailings", "勘误寄送", mailings, mailings_router),
)
