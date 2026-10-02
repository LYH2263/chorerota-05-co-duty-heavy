"""设置读写模块：唯一允许碰 settings 表的地方，键级校验在此收口。

co_duty_min_weight：非负整数，0 = 关闭双人同格（回退单人一格）。
负值、非数字、布尔一律拒写（ValueError → API 层 400），已存值不变。
"""

from app.db import connect

CO_DUTY_MIN_WEIGHT = "co_duty_min_weight"

_DEFAULTS = {CO_DUTY_MIN_WEIGHT: "0"}


def parse_co_duty_min_weight(raw) -> int:
    """把用户输入校验并归一成非负 int；不合法抛 ValueError。"""
    if isinstance(raw, bool):  # True/False 不是合法阈值
        raise ValueError("invalid_co_duty_min_weight")
    if isinstance(raw, int):
        v = raw
    elif isinstance(raw, str) and raw.strip().lstrip("+").isdigit():
        v = int(raw.strip())
    else:
        raise ValueError("invalid_co_duty_min_weight")
    if v < 0:
        raise ValueError("invalid_co_duty_min_weight")
    return v


def _validate(key: str, value) -> str:
    if key == CO_DUTY_MIN_WEIGHT:
        return str(parse_co_duty_min_weight(value))
    return str(value)


def get_all() -> dict:
    """读出全部设置；已知键缺失时补默认值，保证前端/生成路径同口径。"""
    c = connect()
    rows = {r["key"]: r["value"] for r in c.execute("SELECT key,value FROM settings")}
    c.close()
    for k, v in _DEFAULTS.items():
        rows.setdefault(k, v)
    return rows


def get_co_duty_min_weight() -> int:
    return parse_co_duty_min_weight(get_all()[CO_DUTY_MIN_WEIGHT])


def put(updates: dict) -> dict:
    """整批校验通过后写入；任一键非法则整批拒写（ValueError），已存值不变。"""
    validated = {k: _validate(k, v) for k, v in updates.items()}
    c = connect()
    for k, v in validated.items():
        c.execute(
            "INSERT INTO settings(key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
    c.commit()
    c.close()
    return validated
