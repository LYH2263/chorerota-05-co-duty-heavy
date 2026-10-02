"""co-duty 落库:schema 迁移 + 生成结果钉入。

钉(pin)语义:一次生成把当时生效的 co_duty_min_weight 写到 weeks 行,
把每格的主/副角色与降级标记写到 assignments 行。之后只改 settings 里的
现行阈值不会触碰旧周数据 —— 看板与设置页回看的都是这里的落库值。
"""

SCHEMA_COLUMNS = (
    ("weeks", "co_duty_min_weight", "INT"),
    ("assignments", "role", "TEXT NOT NULL DEFAULT 'single'"),
    ("assignments", "degraded", "INT NOT NULL DEFAULT 0"),
)


def ensure_schema(conn) -> None:
    """Idempotent migration: add co-duty columns to pre-existing databases."""
    for table, column, ddl in SCHEMA_COLUMNS:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def pin_generation(conn, week_id: int, threshold: int, slots: list[dict]) -> None:
    """Replace a week's assignments with generated slots and pin the threshold
    used for this run onto the week row. Caller commits."""
    conn.execute("DELETE FROM assignments WHERE week_id=?", (week_id,))
    conn.executemany(
        "INSERT INTO assignments(week_id,day,task_id,member_id,role,degraded)"
        " VALUES (?,?,?,?,?,?)",
        [(week_id, s["day"], s["task_id"], s["member_id"], s["role"], s["degraded"])
         for s in slots],
    )
    conn.execute(
        "UPDATE weeks SET status='ready', co_duty_min_weight=? WHERE id=?",
        (threshold, week_id),
    )
