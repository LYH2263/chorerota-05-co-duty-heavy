"""重活双人同格配对引擎（纯函数，不碰数据库）。

拍板口径（两处取舍，钉死在此，测例按此断言）：

- POLICY_INSUFFICIENT = "fail"
  活跃 clean 成员不足两人且存在 weight >= 阈值的重活时，整次生成失败，
  调用方不得改动 assignments。不做"当日降级单人"的半态——
  看板与设置页回看的永远是上一次完整成功的生成结果，天然同口径。
  （degraded 字段仍随槽位钉下，恒为 0，为未来降级策略留位。）

- ORDER_BY = "phase"
  主/副次序按相位：主 = 相位先落位者，副 = 相位紧次的下一位
  （初始相位即成员 id 升序）。不引入"本周已累积负荷更低者优先"的重排——
  round-robin 本身已均衡负荷，负荷重排会让落位依赖生成历史、难以审计与复算。
"""

POLICY_INSUFFICIENT = "fail"
ORDER_BY = "phase"

ROLE_SOLO = "solo"
ROLE_PRIMARY = "primary"
ROLE_SECONDARY = "secondary"


class CoDutyError(Exception):
    """双人同格生成失败基类。"""


class InsufficientMembersError(CoDutyError):
    """活跃 clean 成员不足两人，无法为重活生成主/副双格（策略：整次失败）。"""


def _norm_tasks(tasks) -> list[tuple[int, int]]:
    """接受 [task_id] 或 [(task_id, weight)] 或 [{id, weight}]，统一成 (id, weight)。"""
    out = []
    for t in tasks:
        if isinstance(t, dict):
            out.append((t["id"], int(t.get("weight", 1))))
        elif isinstance(t, (tuple, list)):
            out.append((int(t[0]), int(t[1])))
        else:
            out.append((int(t), 1))
    return out


def build_slots(member_ids: list[int], tasks, days: int = 7,
                co_duty_min_weight: int = 0) -> list[dict]:
    """生成一周格位。

    co_duty_min_weight <= 0：关闭，逐格单人（role=solo），
        落位顺序与 engines.rota.build_week_slots 完全一致（改造前行为）。
    co_duty_min_weight > 0 且 weight >= 阈值：该 (day, task) 生成主/副两格，
        两人不同、均取自 member_ids（调用方保证其为活跃 clean 集合），
        主=相位先落位、副=次落位，整周共享同一相位、连续消耗。
    存在重活而 len(member_ids) < 2：抛 InsufficientMembersError（整次失败）。
    """
    member_ids = list(member_ids)
    norm = _norm_tasks(tasks)
    threshold = int(co_duty_min_weight or 0)
    co_on = threshold > 0
    heavy = [(tid, w) for tid, w in norm if co_on and w >= threshold]
    if heavy and len(member_ids) < 2:
        raise InsufficientMembersError(
            f"co_duty needs >=2 active clean members, got {len(member_ids)}")
    if not member_ids or not norm:
        return []

    slots = []
    phase = 0
    n = len(member_ids)
    for day in range(days):
        for tid, weight in norm:
            if co_on and weight >= threshold:
                slots.append({
                    "day": day, "task_id": tid,
                    "member_id": member_ids[phase % n],
                    "role": ROLE_PRIMARY, "degraded": 0,
                })
                phase += 1
                slots.append({
                    "day": day, "task_id": tid,
                    "member_id": member_ids[phase % n],
                    "role": ROLE_SECONDARY, "degraded": 0,
                })
                phase += 1
            else:
                slots.append({
                    "day": day, "task_id": tid,
                    "member_id": member_ids[phase % n],
                    "role": ROLE_SOLO, "degraded": 0,
                })
                phase += 1
    return slots
