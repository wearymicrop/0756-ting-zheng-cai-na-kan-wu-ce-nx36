import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from app.errors import InputError
from app.manifest import canonical


class Archive:
    """SQLite 归档存储。

    所有访问经一个进程内共享连接串行化（SQLite 编译为 threadsafety=3，
    可跨线程使用）。高频开/关独立连接在压力下会出现新连接读到旧快照，
    统一连接配合显式事务可消除该竞态；事务边界全部由本类显式控制。
    """

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None：关闭隐式事务，BEGIN/COMMIT 完全显式。
        self._connection = sqlite3.connect(
            self.path, timeout=10, isolation_level=None, check_same_thread=False
        )
        self._ensure_schema()

    def _ensure_schema(self):
        with self._lock:
            self._connection.execute("""CREATE TABLE IF NOT EXISTS runs (
                digest TEXT PRIMARY KEY, payload TEXT NOT NULL
            )""")
            # 已送达台账：只追加，重算只读取、绝不删除或改写（原结论冻结）。
            self._connection.execute("""CREATE TABLE IF NOT EXISTS dispatches (
                run_id TEXT NOT NULL,
                opinion_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, opinion_id)
            )""")
            # 影响册：每个旧案卷一行，重算在单事务内整册替换，中断即回滚。
            self._connection.execute("""CREATE TABLE IF NOT EXISTS impacts (
                run_id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")

    @contextmanager
    def _tx(self):
        with self._lock:
            connection = self._connection
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def find(self, digest):
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM runs WHERE digest = ?", (digest,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def get(self, digest):
        result = self.find(digest)
        if result is None:
            raise InputError("RUN_NOT_FOUND", "找不到该归档", 404)
        return result

    def save(self, record):
        with self._tx() as connection:
            inserted = connection.execute(
                "INSERT INTO runs VALUES (?, ?) ON CONFLICT(digest) DO NOTHING",
                (record["id"], canonical(record)),
            ).rowcount
            payload = connection.execute(
                "SELECT payload FROM runs WHERE digest = ?", (record["id"],)
            ).fetchone()[0]
        return json.loads(payload), not inserted

    # ---- 已送达寄送台账（只追加） ------------------------------------

    def list_dispatches(self, run_id):
        with self._lock:
            rows = self._connection.execute(
                "SELECT payload FROM dispatches WHERE run_id = ? ORDER BY opinion_id", (run_id,)
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def add_dispatches(self, run_id, items, now):
        """幂等追加：同一 (run_id, opinion_id) 不产生重复台账行。"""
        with self._tx() as connection:
            for item in items:
                connection.execute(
                    "INSERT OR IGNORE INTO dispatches (run_id, opinion_id, payload, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (run_id, item["opinion_id"], canonical(item), now),
                )
        return self.list_dispatches(run_id)

    # ---- 旧案卷影响册（事务内整册替换，可回滚） ------------------------

    def get_impact(self, run_id):
        with self._lock:
            row = self._connection.execute(
                "SELECT revision, payload FROM impacts WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return {"revision": row[0], **json.loads(row[1])}

    def replace_impact(self, run_id, register, now, before_commit=None):
        """整册替换。先取写锁再读旧版号；before_commit 抛错时回滚，旧版保留。

        回读必须留在同一把锁、同一连接内：锁外另起查询会与其它写事务交错，
        在高并发下读到提交前的旧快照，造成版本号看似重复。
        """
        with self._tx() as connection:
            previous = connection.execute(
                "SELECT revision FROM impacts WHERE run_id = ?", (run_id,)
            ).fetchone()
            revision = (previous[0] if previous else 0) + 1
            connection.execute("DELETE FROM impacts WHERE run_id = ?", (run_id,))
            connection.execute(
                "INSERT INTO impacts (run_id, revision, payload, updated_at) VALUES (?, ?, ?, ?)",
                (run_id, revision, canonical(register), now),
            )
            if before_commit is not None:
                before_commit(run_id, revision)
            # 仍在同一事务与锁内回读，退出 _tx 时统一提交。
            row = connection.execute(
                "SELECT revision, payload FROM impacts WHERE run_id = ?", (run_id,)
            ).fetchone()
        return {"revision": row[0], **json.loads(row[1])}
