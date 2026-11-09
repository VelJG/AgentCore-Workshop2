"""One local SQLite record per proposal. Approved records are the tickets."""
from contextlib import closing
from pathlib import Path
import sqlite3
from time import time
from uuid import uuid4

from .policy import APPROVAL_TTL_SECONDS, MAX_RECORDS, next_status


class CapacityReached(Exception):
    pass


class Store:
    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=2)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY, content TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'denied')),
                expires_at REAL NOT NULL
            )""")

    def propose(self, content: str) -> str:
        approval_id = str(uuid4())
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM actions WHERE status = 'pending' AND expires_at <= ?", (time(),))
            if db.execute("SELECT count(*) FROM actions").fetchone()[0] >= MAX_RECORDS:
                raise CapacityReached
            db.execute("INSERT INTO actions VALUES (?, ?, 'pending', ?)",
                       (approval_id, content, time() + APPROVAL_TTL_SECONDS))
        return approval_id

    def decide(self, approval_id: str, approve: bool):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM actions WHERE id = ?", (approval_id,)).fetchone()
            if row is None:
                return None
            result = next_status(row["status"], approve=approve, expires_at=row["expires_at"], now=time())
            if row["status"] != result:
                db.execute("UPDATE actions SET status = ? WHERE id = ?", (result, approval_id))
        if result == "approved":
            return {"status": "approved", "ticket_id": approval_id}
        return {"status": "denied"}

    def ticket(self, ticket_id: str):
        with closing(self.connect()) as db:
            row = db.execute("SELECT content FROM actions WHERE id = ? AND status = 'approved'",
                             (ticket_id,)).fetchone()
        return {"ticket_id": ticket_id, "content": row["content"], "status": "Pending"} if row else None
