import re
import sqlite3
from datetime import datetime, timezone

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    kind        TEXT NOT NULL,
    text        TEXT NOT NULL,
    source      TEXT NOT NULL,
    embedding   BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    at         TEXT NOT NULL,
    action     TEXT NOT NULL,
    memory_id  INTEGER,
    detail     TEXT
);
"""

# Deliberately strict: false positives are acceptable, leaked secrets are not.
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(password|passwd|pwd|passphrase|secret|api[_ -]?key|token|private[_ -]?key)\b\s*[:=]?\s*\S+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\b[A-Za-z0-9+/_-]{40,}\b"),
]


class SecretDetected(Exception):
    pass


class MemoryNotFound(LookupError):
    pass


def looks_like_secret(text):
    return any(p.search(text) for p in SECRET_PATTERNS)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MemoryStore:
    def __init__(self, db_path="kora.db", model_name=MODEL_NAME):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        # Overwrite deleted rows on disk so "forget" really forgets.
        self.db.execute("PRAGMA secure_delete = ON")
        self.db.executescript(SCHEMA)
        self.model = SentenceTransformer(model_name, device="cpu")
        self.dim = self.model.get_embedding_dimension()
        self._ids = None
        self._matrix = None

    def _embed(self, text):
        return self.model.encode(text, normalize_embeddings=True).astype(np.float32)

    def _log(self, action, memory_id=None, detail=""):
        # Never log memory text, so deleted memories don't survive in the log.
        self.db.execute(
            "INSERT INTO audit_log (at, action, memory_id, detail) VALUES (?, ?, ?, ?)",
            (now(), action, memory_id, detail),
        )

    def _check_secret(self, text, action):
        if looks_like_secret(text):
            self._log("rejected_secret", detail=action)
            self.db.commit()
            raise SecretDetected()

    def _load_index(self):
        rows = self.db.execute("SELECT id, embedding FROM memories").fetchall()
        self._ids = [r["id"] for r in rows]
        if rows:
            self._matrix = np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
        else:
            self._matrix = np.zeros((0, self.dim), dtype=np.float32)

    def add(self, text, kind="event", source="user"):
        text = text.strip()
        self._check_secret(text, "add")
        cur = self.db.execute(
            "INSERT INTO memories (created_at, kind, text, source, embedding) VALUES (?, ?, ?, ?, ?)",
            (now(), kind, text, source, self._embed(text).tobytes()),
        )
        self._log("add", cur.lastrowid, kind)
        self.db.commit()
        self._ids = None
        return cur.lastrowid

    def get(self, memory_id):
        row = self.db.execute(
            "SELECT id, created_at, kind, text, source FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            raise MemoryNotFound(f"No memory #{memory_id}.")
        return dict(row)

    def latest(self, n=10):
        rows = self.db.execute(
            "SELECT id, created_at, kind, text, source FROM memories ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [dict(r) for r in rows]

    def recall(self, query, k=5, min_score=0.35):
        if self._ids is None:
            self._load_index()
        results = []
        if self._ids:
            scores = self._matrix @ self._embed(query)  # cosine, since vectors are normalized
            for i in np.argsort(-scores)[:k]:
                if scores[i] < min_score:
                    break
                results.append((self.get(self._ids[i]), float(scores[i])))
        self._log("recall", detail=f"{len(results)} results")
        self.db.commit()
        return results

    def edit(self, memory_id, new_text):
        new_text = new_text.strip()
        self._check_secret(new_text, "edit")
        cur = self.db.execute(
            "UPDATE memories SET text = ?, embedding = ? WHERE id = ?",
            (new_text, self._embed(new_text).tobytes(), memory_id),
        )
        if cur.rowcount == 0:
            raise MemoryNotFound(f"No memory #{memory_id}.")
        self._log("edit", memory_id)
        self.db.commit()
        self._ids = None

    def forget(self, memory_id):
        cur = self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if cur.rowcount == 0:
            raise MemoryNotFound(f"No memory #{memory_id}.")
        self._log("forget", memory_id)
        self.db.commit()
        self._ids = None

    def audit(self, n=20):
        rows = self.db.execute(
            "SELECT at, action, memory_id, detail FROM audit_log ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
        return [dict(r) for r in rows]