import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.environ.get("RC_DB_PATH", str(Path(__file__).resolve().parents[1] / "data" / "scada.db"))

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS generators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    customer TEXT NOT NULL DEFAULT '',
    site TEXT NOT NULL DEFAULT '',
    controller_type TEXT NOT NULL CHECK(controller_type IN ('COMAP','DSE')),
    controller_model TEXT NOT NULL DEFAULT '',
    transport TEXT NOT NULL DEFAULT 'rtu_over_tcp'
        CHECK(transport IN ('rtu_over_tcp','modbus_tcp')),
    modbus_unit INTEGER NOT NULL DEFAULT 1,
    listen_port INTEGER NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS telemetry (
    generator_id INTEGER PRIMARY KEY,
    connected INTEGER NOT NULL DEFAULT 0,
    poll_ok INTEGER NOT NULL DEFAULT 0,
    peer TEXT NOT NULL DEFAULT '',
    last_seen INTEGER,
    last_error TEXT NOT NULL DEFAULT '',
    values_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(generator_id) REFERENCES generators(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generator_id INTEGER,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY(generator_id) REFERENCES generators(id) ON DELETE CASCADE
);
"""

@contextmanager
def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)

def next_port():
    with connect() as conn:
        row = conn.execute("SELECT MAX(listen_port) AS p FROM generators").fetchone()
        return max(15001, (row["p"] or 15000) + 1)

def list_generators():
    with connect() as conn:
        rows = conn.execute("""
            SELECT g.*, COALESCE(t.connected,0) connected, COALESCE(t.poll_ok,0) poll_ok,
                   COALESCE(t.peer,'') peer, t.last_seen, COALESCE(t.last_error,'') last_error,
                   COALESCE(t.values_json,'{}') values_json
            FROM generators g LEFT JOIN telemetry t ON t.generator_id=g.id
            ORDER BY g.code
        """).fetchall()
    return [_row_generator(r) for r in rows]

def get_generator(generator_id):
    with connect() as conn:
        row = conn.execute("""
            SELECT g.*, COALESCE(t.connected,0) connected, COALESCE(t.poll_ok,0) poll_ok,
                   COALESCE(t.peer,'') peer, t.last_seen, COALESCE(t.last_error,'') last_error,
                   COALESCE(t.values_json,'{}') values_json
            FROM generators g LEFT JOIN telemetry t ON t.generator_id=g.id
            WHERE g.id=?
        """, (generator_id,)).fetchone()
    return _row_generator(row) if row else None

def create_generator(data):
    port = int(data.get("listen_port") or next_port())
    now = int(time.time())
    with connect() as conn:
        cur = conn.execute("""
            INSERT INTO generators
            (code,name,customer,site,controller_type,controller_model,transport,modbus_unit,listen_port,enabled,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["code"].strip().upper(), data["name"].strip(), data.get("customer","").strip(),
            data.get("site","").strip(), data["controller_type"].strip().upper(),
            data.get("controller_model","").strip(), data.get("transport","rtu_over_tcp"),
            int(data.get("modbus_unit",1)), port, 1 if data.get("enabled",True) else 0, now
        ))
        gid = cur.lastrowid
        conn.execute("INSERT INTO telemetry(generator_id) VALUES (?)", (gid,))
        conn.execute("INSERT INTO events(generator_id,level,message,created_at) VALUES (?,?,?,?)",
                     (gid,"INFO",f"Gerador cadastrado na porta TCP {port}",now))
    return get_generator(gid)

def update_generator(generator_id, data):
    allowed = ["code","name","customer","site","controller_type","controller_model","transport",
               "modbus_unit","listen_port","enabled"]
    fields=[]; values=[]
    for key in allowed:
        if key in data:
            val=data[key]
            if key in ("controller_type","code"): val=str(val).upper()
            if key in ("modbus_unit","listen_port","enabled"): val=int(val)
            fields.append(f"{key}=?"); values.append(val)
    if not fields:
        return get_generator(generator_id)
    values.append(generator_id)
    with connect() as conn:
        conn.execute(f"UPDATE generators SET {','.join(fields)} WHERE id=?", values)
    return get_generator(generator_id)

def delete_generator(generator_id):
    with connect() as conn:
        conn.execute("DELETE FROM generators WHERE id=?", (generator_id,))

def update_telemetry(generator_id, *, connected=None, poll_ok=None, peer=None, values=None, error=None):
    now=int(time.time())
    with connect() as conn:
        existing=conn.execute("SELECT * FROM telemetry WHERE generator_id=?", (generator_id,)).fetchone()
        if not existing:
            conn.execute("INSERT INTO telemetry(generator_id) VALUES (?)", (generator_id,))
            existing=conn.execute("SELECT * FROM telemetry WHERE generator_id=?", (generator_id,)).fetchone()
        conn.execute("""
            UPDATE telemetry SET connected=?,poll_ok=?,peer=?,last_seen=?,last_error=?,values_json=?
            WHERE generator_id=?
        """, (
            int(existing["connected"] if connected is None else connected),
            int(existing["poll_ok"] if poll_ok is None else poll_ok),
            existing["peer"] if peer is None else str(peer),
            now,
            existing["last_error"] if error is None else str(error),
            existing["values_json"] if values is None else json.dumps(values, ensure_ascii=False),
            generator_id
        ))

def add_event(generator_id, level, message):
    with connect() as conn:
        conn.execute("INSERT INTO events(generator_id,level,message,created_at) VALUES (?,?,?,?)",
                     (generator_id,level,message,int(time.time())))

def recent_events(limit=50):
    with connect() as conn:
        rows=conn.execute("""
          SELECT e.*, g.code FROM events e LEFT JOIN generators g ON g.id=e.generator_id
          ORDER BY e.id DESC LIMIT ?
        """,(limit,)).fetchall()
    return [dict(r) for r in rows]

def dashboard():
    gens=list_generators()
    now=int(time.time())
    online=0; operating=0; alarm=0
    for g in gens:
        fresh=g["last_seen"] and now-g["last_seen"] < 15
        if g["connected"] and fresh: online += 1
        vals=g["values"]
        text=" ".join(str(v).lower() for v in vals.values())
        if "running" in text or "operating" in text or "1800" in text: operating += 1
        if "alarm" in text or g["last_error"]: alarm += 1
    return {"total":len(gens),"online":online,"offline":len(gens)-online,"operating":operating,"alarm":alarm}

def _row_generator(r):
    if not r: return None
    d=dict(r)
    try: d["values"]=json.loads(d.pop("values_json","{}") or "{}")
    except Exception: d["values"]={}
    d["enabled"]=bool(d["enabled"]); d["connected"]=bool(d["connected"]); d["poll_ok"]=bool(d["poll_ok"])
    return d
