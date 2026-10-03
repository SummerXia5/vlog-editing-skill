"""Durable local project state. Each connection is scoped to one operation."""
import json
import sqlite3
import time
import uuid
from pathlib import Path


def uid():
    return uuid.uuid4().hex


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'studio.sqlite3'
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS objects (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                    project TEXT NOT NULL, data TEXT NOT NULL, created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS object_project ON objects(project, kind);
            ''')

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def put(self, kind, project, data, object_id=None):
        object_id = object_id or uid()
        record = dict(data, id=object_id)
        with self.connect() as db:
            db.execute('INSERT INTO objects VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
                       (object_id, kind, project, json.dumps(record, ensure_ascii=False), time.time()))
        return record

    def get(self, object_id, kind=None):
        with self.connect() as db:
            row = db.execute('SELECT kind,data FROM objects WHERE id=?', (object_id,)).fetchone()
        if not row or (kind and row[0] != kind):
            raise ValueError('Record not found')
        return json.loads(row[1])

    def list(self, kind, project=None):
        with self.connect() as db:
            sql, args = 'SELECT data FROM objects WHERE kind=?', [kind]
            if project is not None:
                sql += ' AND project=?'
                args.append(project)
            rows = db.execute(sql + ' ORDER BY created', args).fetchall()
        return [json.loads(row[0]) for row in rows]

    def delete(self, object_id, kind):
        with self.connect() as db:
            db.execute('DELETE FROM objects WHERE id=? AND kind=?', (object_id, kind))
