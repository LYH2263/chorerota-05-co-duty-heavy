"""co_duty_min_weight 设置读写:校验、读取、写入。

阈值语义:0 = 关闭双人(回退改造前单人一格);>0 = weight >= 阈值的任务
每日生成主/副两格。拒写规则:负数、非整数、非数字一律 ValueError(由
API 层转 400),不把脏值写进 settings 表。
"""

KEY = "co_duty_min_weight"
DEFAULT = 0


def validate_threshold(raw) -> int:
    """Return the threshold as a non-negative int, or raise ValueError.

    Accepts int and digit strings ("0", "3"); rejects bools, floats,
    negatives, blanks and non-numeric strings.
    """
    if isinstance(raw, bool):  # bool is a subclass of int — reject explicitly
        raise ValueError(f"{KEY} must be a non-negative integer")
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str) and raw.strip().isdigit():
        value = int(raw.strip())
    else:
        raise ValueError(f"{KEY} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{KEY} must be >= 0")
    return value


def get_threshold(conn) -> int:
    """Live threshold from settings; missing or corrupt value falls back to 0
    (disabled) so generation never crashes on legacy rows."""
    row = conn.execute("SELECT value FROM settings WHERE key=?", (KEY,)).fetchone()
    if row is None:
        return DEFAULT
    try:
        return validate_threshold(row["value"])
    except ValueError:
        return DEFAULT


def set_threshold(conn, raw) -> int:
    """Validate then upsert; returns the stored int. Raises ValueError on bad input."""
    value = validate_threshold(raw)
    conn.execute(
        "INSERT INTO settings(key,value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (KEY, str(value)),
    )
    return value
