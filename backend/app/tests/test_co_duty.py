"""配对引擎测例：关闭回退 / 开启双人 / 相位连续 / 不足两人取舍 / 主副次序。"""
import pytest

from app.engines import co_duty
from app.engines.rota import build_week_slots as legacy_slots


def _strip(slots):
    return [{"day": s["day"], "task_id": s["task_id"], "member_id": s["member_id"]}
            for s in slots]


def test_disabled_falls_back_to_legacy_single():
    """阈值 0 = 关闭：落位与改造前 build_week_slots 完全一致，全部 solo。"""
    tasks = [(10, 3), (20, 1)]  # 即使有重活也不拆
    got = co_duty.build_slots([1, 2, 3], tasks, days=7, co_duty_min_weight=0)
    assert _strip(got) == legacy_slots([1, 2, 3], [10, 20], days=7)
    assert {s["role"] for s in got} == {"solo"}
    assert all(s["degraded"] == 0 for s in got)


def test_enabled_pairs_heavy_task_per_day():
    """开启后重活每天主/副两格，轻活仍单人一格。"""
    got = co_duty.build_slots([1, 2, 3], [(10, 3), (20, 1)], days=2,
                              co_duty_min_weight=2)
    day0 = [s for s in got if s["day"] == 0]
    assert len(day0) == 3  # 重活 2 格 + 轻活 1 格
    pair = [s for s in day0 if s["task_id"] == 10]
    assert [s["role"] for s in pair] == ["primary", "secondary"]
    assert pair[0]["member_id"] != pair[1]["member_id"]
    assert {pair[0]["member_id"], pair[1]["member_id"]} <= {1, 2, 3}
    solo = [s for s in day0 if s["task_id"] == 20]
    assert len(solo) == 1 and solo[0]["role"] == "solo"


def test_phase_consumed_continuously_across_cells_and_days():
    """相位连续消耗：重活吃 2 步、轻活吃 1 步，跨天不回退。

    3 成员 + 单个重活：day0 主1副2，day1 主3副1，day2 主2副3。
    """
    got = co_duty.build_slots([1, 2, 3], [(10, 5)], days=3, co_duty_min_weight=2)
    seq = [(s["member_id"], s["role"]) for s in got]
    assert seq == [
        (1, "primary"), (2, "secondary"),
        (3, "primary"), (1, "secondary"),
        (2, "primary"), (3, "secondary"),
    ]


def test_phase_order_decides_primary_not_load():
    """拍板：主=相位先落位者（初始即成员 id 升序），与负荷无关、可复算。"""
    assert co_duty.ORDER_BY == "phase"
    got = co_duty.build_slots([7, 9], [(10, 2)], days=1, co_duty_min_weight=1)
    assert (got[0]["member_id"], got[0]["role"]) == (7, "primary")
    assert (got[1]["member_id"], got[1]["role"]) == (9, "secondary")


def test_mixed_weights_share_one_phase():
    """重活两格与轻活一格共用同一相位流。"""
    got = co_duty.build_slots([1, 2, 3], [(10, 3), (20, 1)], days=1,
                              co_duty_min_weight=2)
    assert [s["member_id"] for s in got] == [1, 2, 3]


def test_insufficient_members_fails_whole_generation():
    """拍板 POLICY_INSUFFICIENT=fail：活跃 clean 不足两人 → 整次抛错。"""
    assert co_duty.POLICY_INSUFFICIENT == "fail"
    with pytest.raises(co_duty.InsufficientMembersError):
        co_duty.build_slots([1], [(10, 3)], days=7, co_duty_min_weight=2)
    with pytest.raises(co_duty.InsufficientMembersError):
        co_duty.build_slots([], [(10, 3)], days=7, co_duty_min_weight=2)


def test_insufficient_members_ok_when_disabled_or_no_heavy():
    """关闭时单成员照常（改造前行为）；开启但无重活也不触发失败。"""
    got = co_duty.build_slots([1], [(10, 3)], days=2, co_duty_min_weight=0)
    assert len(got) == 2 and all(s["role"] == "solo" for s in got)
    got = co_duty.build_slots([1], [(10, 1)], days=2, co_duty_min_weight=5)
    assert len(got) == 2 and all(s["role"] == "solo" for s in got)


def test_slots_pin_role_and_degraded():
    """生成即钉：每格都带 role 与 degraded（fail 策略下恒 0）。"""
    got = co_duty.build_slots([1, 2], [(10, 2)], days=1, co_duty_min_weight=1)
    assert got[0]["degraded"] == 0 and got[1]["degraded"] == 0
    assert {s["role"] for s in got} == {"primary", "secondary"}
