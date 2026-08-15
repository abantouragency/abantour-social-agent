"""
state_db.py — lightweight SQLite store for staged content + publish state.
Lives on Render (orchestrator side). The PC producer uploads rendered media
+ metadata via the web API; the control bot reads/writes this DB.
"""
import os, json, sqlite3, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "agent_state.db")


def _conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    c = _conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS items (
        id TEXT PRIMARY KEY,
        pillar TEXT,
        slot TEXT,
        topic TEXT,
        reel_url TEXT,
        info_url TEXT,
        caption TEXT,
        hook TEXT,
        status TEXT DEFAULT 'staged',   -- staged | published | rejected
        created_at TEXT,
        published_at TEXT,
        platforms TEXT DEFAULT '[]'     -- json list: telegram, instagram
    );
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        level TEXT,
        msg TEXT
    );
    """)
    c.commit(); c.close()


def add_item(rec):
    c = _conn()
    c.execute("""INSERT OR REPLACE INTO items
        (id,pillar,slot,topic,reel_url,info_url,caption,hook,status,created_at,platforms)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (rec["id"], rec.get("pillar"), rec.get("slot"), rec.get("topic"),
         rec.get("reel_url"), rec.get("info_url"), rec.get("caption"),
         rec.get("hook"), rec.get("status", "staged"),
         rec.get("created_at", _now()), json.dumps(rec.get("platforms", []), ensure_ascii=False)))
    c.commit(); c.close()


def pending():
    c = _conn()
    rows = c.execute("SELECT * FROM items WHERE status='staged' ORDER BY created_at").fetchall()
    c.close()
    return [dict(r) for r in rows]


def set_published(item_id, platforms):
    c = _conn()
    c.execute("UPDATE items SET status='published', published_at=?, platforms=? WHERE id=?",
              (_now(), json.dumps(platforms, ensure_ascii=False), item_id))
    c.commit(); c.close()


def set_rejected(item_id):
    c = _conn()
    c.execute("UPDATE items SET status='rejected' WHERE id=?", (item_id,))
    c.commit(); c.close()


def stats():
    c = _conn()
    total = c.execute("SELECT COUNT(*) n FROM items").fetchone()["n"]
    staged = c.execute("SELECT COUNT(*) n FROM items WHERE status='staged'").fetchone()["n"]
    published = c.execute("SELECT COUNT(*) n FROM items WHERE status='published'").fetchone()["n"]
    c.close()
    return {"total": total, "staged": staged, "published": published}


def log(level, msg):
    c = _conn()
    c.execute("INSERT INTO logs (ts,level,msg) VALUES (?,?,?)", (_now(), level, msg[:500]))
    c.commit(); c.close()


def recent_logs(n=20):
    c = _conn()
    rows = c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def set_flag(key, value):
    c = _conn()
    c.execute("""CREATE TABLE IF NOT EXISTS flags (k TEXT PRIMARY KEY, v TEXT)""")
    c.execute("INSERT OR REPLACE INTO flags (k,v) VALUES (?,?)", (key, str(value)))
    c.commit(); c.close()


def get_flag(key, default=None):
    c = _conn()
    row = c.execute("SELECT v FROM flags WHERE k=?", (key,)).fetchone()
    c.close()
    return row["v"] if row else default


def add_pc_request(pillar):
    c = _conn()
    c.execute("""CREATE TABLE IF NOT EXISTS pc_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pillar TEXT,
        ts TEXT,
        status TEXT DEFAULT 'pending'
    )""")
    c.execute("INSERT INTO pc_requests (pillar, ts, status) VALUES (?,?,?)",
              (pillar, _now(), "pending"))
    c.commit(); c.close()


def take_pc_requests():
    """Return pending PC requests and mark them done."""
    c = _conn()
    c.execute("""CREATE TABLE IF NOT EXISTS pc_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pillar TEXT, ts TEXT, status TEXT DEFAULT 'pending')""")
    rows = c.execute("SELECT * FROM pc_requests WHERE status='pending' ORDER BY id").fetchall()
    ids = [r["id"] for r in rows]
    if ids:
        c.execute(f"UPDATE pc_requests SET status='done' WHERE id IN ({','.join('?'*len(ids))})", ids)
        c.commit()
    c.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init()
    print("state_db ready at", DB)
