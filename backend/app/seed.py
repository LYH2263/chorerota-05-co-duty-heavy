from app.db import connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY, name TEXT, active INT, data_quality TEXT);
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, title TEXT, weight INT, data_quality TEXT);
CREATE TABLE IF NOT EXISTS weeks(id INTEGER PRIMARY KEY, label TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY AUTOINCREMENT, week_id INT, day INT, task_id INT, member_id INT);
CREATE TABLE IF NOT EXISTS swap_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, week_id INT, a_day INT, a_task INT, b_day INT, b_task INT, status TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""

# 双人同格新增列：老库 ALTER 补齐，新库由下方兜底（IF NOT EXISTS 不覆盖已有行）。
_MIGRATIONS = [
    "ALTER TABLE assignments ADD COLUMN role TEXT NOT NULL DEFAULT 'solo'",
    "ALTER TABLE assignments ADD COLUMN degraded INT NOT NULL DEFAULT 0",
    "ALTER TABLE weeks ADD COLUMN co_duty_min_weight INT NOT NULL DEFAULT 0",
]


def _migrate(c):
    cols = {t: {r["name"] for r in c.execute(f"PRAGMA table_info({t})")}
            for t in ("assignments", "weeks")}
    for sql in _MIGRATIONS:
        table = sql.split()[2]
        col = sql.split()[5]
        if col not in cols[table]:
            c.execute(sql)


def init_db():
    c = connect()
    c.executescript(_SCHEMA)
    _migrate(c)
    # 默认设置行对老库同样补齐
    c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('co_duty_min_weight','0')")
    if c.execute("SELECT COUNT(*) c FROM members").fetchone()["c"] == 0:
        c.executemany("INSERT INTO members(name,active,data_quality) VALUES (?,?,?)", [
            ("阿明", 1, "clean"), ("小雨", 1, "clean"), ("爷爷", 1, "clean"),
            ("幽灵成员", 0, "dirty"),
        ])
        c.executemany("INSERT INTO tasks(title,weight,data_quality) VALUES (?,?,?)", [
            ("洗碗", 1, "clean"), ("倒垃圾", 1, "clean"), ("扫地", 2, "clean"),
            ("大扫除", 3, "clean"),
            ("负权重任务", -1, "dirty"),
        ])
        c.execute("INSERT INTO weeks(label,status) VALUES ('第12周','draft')")
        c.execute("INSERT INTO settings(key,value) VALUES ('household','绿纸之家')")
    c.commit()
    c.close()
