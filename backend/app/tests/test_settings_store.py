"""设置读写测例：默认值、合法写入、阈值拒写。"""
import pytest

from app import seed, settings_store


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    seed.init_db()
    return tmp_path


def test_default_threshold_is_zero(fresh_db):
    assert settings_store.get_co_duty_min_weight() == 0
    assert settings_store.get_all()["co_duty_min_weight"] == "0"


def test_write_and_read_back(fresh_db):
    settings_store.put({"co_duty_min_weight": 3})
    assert settings_store.get_co_duty_min_weight() == 3
    settings_store.put({"co_duty_min_weight": "2"})  # 数字字符串也收
    assert settings_store.get_co_duty_min_weight() == 2


@pytest.mark.parametrize("bad", [-1, "-2", "abc", "", 1.5, True, None, [1]])
def test_invalid_threshold_rejected_and_value_kept(fresh_db, bad):
    settings_store.put({"co_duty_min_weight": 4})
    with pytest.raises(ValueError):
        settings_store.put({"co_duty_min_weight": bad})
    assert settings_store.get_co_duty_min_weight() == 4  # 拒写后旧值不变


def test_batch_with_invalid_key_writes_nothing(fresh_db):
    """整批校验：同批任一非法 → 合法键也不落库。"""
    settings_store.put({"household": "旧家"})
    with pytest.raises(ValueError):
        settings_store.put({"household": "新家", "co_duty_min_weight": -1})
    assert settings_store.get_all()["household"] == "旧家"


def test_zero_disables_co_duty(fresh_db):
    settings_store.put({"co_duty_min_weight": 5})
    settings_store.put({"co_duty_min_weight": 0})
    assert settings_store.get_co_duty_min_weight() == 0
