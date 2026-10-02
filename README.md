# Chorerota · 家庭值日轮转

底座：成员+任务 → round-robin 生成周表 → 申请对调 → 确认改表。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5100 |
| API | 10100 |

```bash
docker compose up --build
pytest backend/app/tests
```

种子含 clean/dirty。0-1 空桩：`streak_badge` / `skip_week` / `chore_photo`。

## 重活双人同格（co-duty）

设置页登记 `co_duty_min_weight`（非负整数，0=关闭；负值/非数字拒写 400）。
开启后 `weight ≥ 阈值` 的任务每天落主/副两格：两人不同、均来自活跃 clean 集合，
全周共享同一相位连续消耗（重活 2 步、轻活 1 步）。两处拍板钉在
`backend/app/engines/co_duty.py`：不足两人 → 整次生成失败不改 assignments；
主副次序 → 按相位（主先副后）。生成把阈值钉进 `weeks.co_duty_min_weight`、
主副与降级标记钉进 `assignments.role/degraded`；只改现行阈值不拆旧周双人格，
看板与设置页回看同源钉值。模块边界：`engines/co_duty.py`（纯配对）/
`settings_store.py`（设置读写校验）/`weeks_store.py`（落库与看板读模型）。
