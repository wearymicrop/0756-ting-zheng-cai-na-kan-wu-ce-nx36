import hashlib
import json
from datetime import datetime, timezone

from app import settings
from app.settings import PROJECT


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha256(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def rule_version():
    # 动态读取，测试可 monkeypatch settings.RULE_VERSION 模拟规则升级。
    return settings.RULE_VERSION


def identity(data, sample):
    return sha256([PROJECT, rule_version(), sample, data])


def make_manifest(data, sample, digest, elapsed_ms):
    return {
        "digest": digest,
        "input_sha256": sha256(data),
        "rule_version": rule_version(),
        "project": PROJECT,
        "sample": sample,
        "elapsed_ms": elapsed_ms,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
