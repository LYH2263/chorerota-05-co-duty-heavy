"""Co-duty pairing engine: heavy tasks get a primary+secondary slot pair per day.

拍板决策(两处取舍已定,测试锁定):
1. 活跃 clean 成员不足两人时:不整次失败,该任务当日降级为单人格并打
   degraded=1 标记。理由:整次失败是对改造前行为的回归(单人家庭原本能生成),
   降级+标记既保可用又保可审计;看板与设置页读同一份落库标记,口径一致。
2. 主/副次序:当前周已累积负荷(已分得任务的 weight 之和)更低者为主,
   并列时成员 id 小者为主。比纯 id 排序更公平,且确定性可测。

相位连续消耗:双人格从同一轮转序列连续取两人(idx, idx+1),主/副标签
只在 pair 内部按上述规则贴,不改变相位消耗顺序。
"""

ROLE_SINGLE = "single"
ROLE_PRIMARY = "primary"
ROLE_SECONDARY = "secondary"


def build_week_slots(
    member_ids: list[int],
    tasks: list[dict],
    days: int = 7,
    co_duty_min_weight: int = 0,
) -> list[dict]:
    """Round-robin weekly slots with co-duty pairs for heavy tasks.

    member_ids: active+clean member ids, ascending by id.
    tasks: [{"id": int, "weight": int}] clean tasks with weight > 0, ascending by id.
    co_duty_min_weight: tasks with weight >= threshold get two slots per day.
        0 (or negative) disables co-duty entirely — output is exactly the
        pre-change single-slot round-robin, every slot role='single', degraded=0.

    Returns [{"day", "task_id", "member_id", "role", "degraded"}]:
      role: 'single' | 'primary' | 'secondary'
      degraded: 1 when a heavy slot fell back to single because fewer than two
                active clean members exist; generation still succeeds.
    """
    if not member_ids or not tasks:
        return []
    enabled = co_duty_min_weight > 0
    n = len(member_ids)
    loads = {m: 0 for m in member_ids}
    slots: list[dict] = []
    idx = 0
    for day in range(days):
        for task in tasks:
            tid = task["id"]
            weight = task["weight"]
            heavy = enabled and weight >= co_duty_min_weight
            if heavy and n >= 2:
                pair = (member_ids[idx % n], member_ids[(idx + 1) % n])
                idx += 2
                primary, secondary = sorted(pair, key=lambda m: (loads[m], m))
                slots.append({"day": day, "task_id": tid, "member_id": primary,
                              "role": ROLE_PRIMARY, "degraded": 0})
                slots.append({"day": day, "task_id": tid, "member_id": secondary,
                              "role": ROLE_SECONDARY, "degraded": 0})
                loads[primary] += weight
                loads[secondary] += weight
            elif heavy:  # n == 1: degrade to a single marked slot
                mid = member_ids[idx % n]
                idx += 1
                slots.append({"day": day, "task_id": tid, "member_id": mid,
                              "role": ROLE_SINGLE, "degraded": 1})
                loads[mid] += weight
            else:
                mid = member_ids[idx % n]
                idx += 1
                slots.append({"day": day, "task_id": tid, "member_id": mid,
                              "role": ROLE_SINGLE, "degraded": 0})
                loads[mid] += weight
    return slots
