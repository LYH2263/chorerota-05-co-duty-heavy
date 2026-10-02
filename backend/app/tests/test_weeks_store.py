"""落库测例：开启双人钉值 / 改阈值不拆旧周 / 不足两人整次失败 / 关闭回退。"""
import pytest

from app import seed, settings_store, weeks_store
from app.db import connect
from app.engines.co_duty import InsufficientMembersError


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    seed.init_db()
    return tmp_path


def _rows(week_id=1):
    c = connect()
    rows = [dict(r) for r in c.execute(
        "SELECT day,task_id,member_id,role,degraded FROM assignments "
        "WHERE week_id=? ORDER BY id", (week_id,))]
    pinned = c.execute(
        "SELECT co_duty_min_weight FROM weeks WHERE id=?", (week_id,)).fetchone()
    c.close()
    return rows, pinned["co_duty_min_weight"]


def test_generate_dual_pins_threshold_roles_and_degraded(fresh_db):
    settings_store.put({"co_duty_min_weight": 2})
    out = weeks_store.generate_week(1, days=7)
    assert out["co_duty_min_weight"] == 2
    rows, pinned = _rows()
    assert pinned == 2  # 阈值钉进周行
    heavy = [r for r in rows if r["task_id"] in (3, 4)]  # 扫地 w2 / 大扫除 w3
    light = [r for r in rows if r["task_id"] in (1, 2)]
    assert {r["role"] for r in heavy} == {"primary", "secondary"}
    assert {r["role"] for r in light} == {"solo"}
    # 每个 (day, 重活) 恰好主副各一、两人不同
    from collections import defaultdict
    cells = defaultdict(list)
    for r in heavy:
        cells[(r["day"], r["task_id"])].append(r)
    for cell in cells.values():
        assert len(cell) == 2
        assert {c["role"] for c in cell} == {"primary", "secondary"}
        assert cell[0]["member_id"] != cell[1]["member_id"]
    assert all(r["degraded"] == 0 for r in rows)  # 降级标记随格钉下


def test_changing_current_threshold_keeps_old_week_pairs(fresh_db):
    """只改现行阈值不得拆旧周双人格：看板仍按已钉阈值与主副渲染。"""
    settings_store.put({"co_duty_min_weight": 2})
    weeks_store.generate_week(1, days=7)
    before, pinned_before = _rows()
    settings_store.put({"co_duty_min_weight": 0})  # 改现行阈值（甚至关闭）
    after, pinned_after = _rows()
    assert after == before            # 双人格一行没动
    assert pinned_before == pinned_after == 2
    board = weeks_store.week_board(1)
    assert board["week"]["co_duty_min_weight"] == 2
    roles = {a["role"] for a in board["assignments"]}
    assert {"primary", "secondary"} <= roles


def test_insufficient_members_fails_without_touching_assignments(fresh_db):
    """活跃 clean 不足两人：整次失败，assignments 与已钉阈值保持原样。"""
    settings_store.put({"co_duty_min_weight": 0})
    weeks_store.generate_week(1, days=7)
    before, pinned_before = _rows()
    assert before and pinned_before == 0

    c = connect()
    c.execute("UPDATE members SET active=0 WHERE id != 1")  # 只剩 1 个活跃 clean
    c.commit(); c.close()
    settings_store.put({"co_duty_min_weight": 1})  # 开启且有重活

    with pytest.raises(InsufficientMembersError):
        weeks_store.generate_week(1, days=7)
    after, pinned_after = _rows()
    assert after == before            # 一行未改
    assert pinned_after == pinned_before


def test_disabled_generate_matches_legacy_shape(fresh_db):
    """阈值 0 落库：7 天 × clean 正权重任务数 格，全部 solo。"""
    settings_store.put({"co_duty_min_weight": 0})
    out = weeks_store.generate_week(1, days=7)
    rows, pinned = _rows()
    assert pinned == 0
    assert out["count"] == 7 * 4      # 洗碗/倒垃圾/扫地/大扫除（负权重 dirty 排除）
    assert len(rows) == out["count"]
    assert {r["role"] for r in rows} == {"solo"}


def test_board_reads_same_pinned_values_as_settings(fresh_db):
    """看板与设置回看同口径：两处读到的已钉阈值一致。"""
    settings_store.put({"co_duty_min_weight": 3})
    weeks_store.generate_week(1, days=7)
    board = weeks_store.week_board(1)
    assert board["week"]["co_duty_min_weight"] == 3
    assert settings_store.get_co_duty_min_weight() == 3  # 现行值同源
    pairs = [a for a in board["assignments"] if a["role"] == "secondary"]
    assert pairs and all(a["degraded"] == 0 for a in pairs)
