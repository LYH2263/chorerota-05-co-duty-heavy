"""周表落库模块：生成写库 + 看板读模型，是唯一碰 assignments/weeks 生成口径的地方。

钉值语义：
- 生成成功时把当时生效的 co_duty_min_weight 钉进 weeks 行，
  并把每格 role(primary/secondary/solo) 与 degraded 钉进 assignments 行。
- 之后只改设置里的现行阈值，绝不回写旧周——旧周看板仍按已钉双人格渲染。
- 引擎抛 InsufficientMembersError 时（拍板：整次失败），本函数不写任何行，
  assignments 与 weeks 保持原样。
"""

from app.db import connect
from app.engines import co_duty
from app.settings_store import get_co_duty_min_weight


def generate_week(week_id: int, days: int = 7) -> dict:
    """按现行阈值生成一周并落库；返回 {count, slots, co_duty_min_weight}。"""
    c = connect()
    try:
        week = c.execute("SELECT * FROM weeks WHERE id=?", (week_id,)).fetchone()
        if not week:
            raise KeyError("week not found")
        mids = [r["id"] for r in c.execute(
            "SELECT id FROM members WHERE active=1 AND data_quality='clean' ORDER BY id")]
        tasks = [(r["id"], r["weight"]) for r in c.execute(
            "SELECT id,weight FROM tasks WHERE data_quality='clean' AND weight>0 ORDER BY id")]
        threshold = get_co_duty_min_weight()
        # 引擎先算完（不足两人在此抛错），失败时下方 DELETE/INSERT 一行都不会执行。
        slots = co_duty.build_slots(mids, tasks, days=days, co_duty_min_weight=threshold)
        c.execute("DELETE FROM assignments WHERE week_id=?", (week_id,))
        for s in slots:
            c.execute(
                "INSERT INTO assignments(week_id,day,task_id,member_id,role,degraded) "
                "VALUES (?,?,?,?,?,?)",
                (week_id, s["day"], s["task_id"], s["member_id"], s["role"], s["degraded"]))
        c.execute(
            "UPDATE weeks SET status='ready', co_duty_min_weight=? WHERE id=?",
            (threshold, week_id))
        c.commit()
        return {"count": len(slots), "slots": slots, "co_duty_min_weight": threshold}
    finally:
        c.close()


def week_board(week_id: int) -> dict | None:
    """看板读模型：周行（含已钉阈值）+ 带 role/degraded 的格，主副按落库序。"""
    c = connect()
    week = c.execute("SELECT * FROM weeks WHERE id=?", (week_id,)).fetchone()
    if not week:
        c.close()
        return None
    assigns = [dict(r) for r in c.execute(
        "SELECT * FROM assignments WHERE week_id=? ORDER BY id", (week_id,))]
    members = {r["id"]: r["name"] for r in c.execute("SELECT id,name FROM members")}
    tasks = {r["id"]: r["title"] for r in c.execute("SELECT id,title FROM tasks")}
    c.close()
    for a in assigns:
        a["member_name"] = members.get(a["member_id"], "?")
        a["task_title"] = tasks.get(a["task_id"], "?")
    return {"week": dict(week), "assignments": assigns}
