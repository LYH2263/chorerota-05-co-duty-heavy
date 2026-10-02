<template>
  <div>
    <h1 class="brand">设置</h1>
    <label>家庭名 <input v-model="household" /></label>
    <label>
      双人同格最小权重 co_duty_min_weight
      <input type="number" min="0" step="1" v-model.number="coDutyMinWeight" />
    </label>
    <p class="muted">
      0 = 关闭（单人一格）；&gt;0 时 weight ≥ 阈值的重活每天落主/副两人。
      活跃 clean 成员不足两人则整次生成失败、不改现有周表。
    </p>
    <button @click="save">保存</button>
    <p v-if="err" class="err">{{ err }}</p>
    <p v-if="saved" class="muted">已保存（只影响之后生成，不拆已生成周的双人格）</p>

    <h2>本周回看（与看板同源钉值）</h2>
    <p class="muted">
      已钉阈值：{{ pinned.co_duty_min_weight ?? 0 }} ·
      双人格 {{ pinned.dualCells }} 处 · 降级 {{ pinned.degraded }} 处
    </p>
    <ul class="list" v-if="pinned.pairs.length">
      <li v-for="(p, i) in pinned.pairs" :key="i">
        Day {{ p.day }} · {{ p.task_title }}：主 {{ p.primary }} / 副 {{ p.secondary }}
      </li>
    </ul>
    <p class="muted" style="margin-top:16px">健康检查：{{ health }}</p>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const household = ref('')
const coDutyMinWeight = ref(0)
const health = ref('')
const err = ref('')
const saved = ref(false)
const pinned = ref({ pairs: [], dualCells: 0, degraded: 0, co_duty_min_weight: 0 })
const weekId = 1
async function load() {
  const s = await api('/settings')
  household.value = s.household || ''
  coDutyMinWeight.value = Number(s.co_duty_min_weight ?? 0)
  const h = await api('/health'); health.value = JSON.stringify(h)
  // 回看与看板读同一份钉值：周行阈值 + assignments 的主/副
  const b = await api('/weeks/' + weekId + '/board')
  const byCell = new Map()
  let degraded = 0
  for (const a of b.assignments || []) {
    const k = a.day + ':' + a.task_id
    if (!byCell.has(k)) byCell.set(k, { day: a.day, task_title: a.task_title })
    const cell = byCell.get(k)
    if (a.role === 'primary') cell.primary = a.member_name
    if (a.role === 'secondary') cell.secondary = a.member_name
    if (a.degraded) degraded++
  }
  const pairs = [...byCell.values()].filter(c => c.primary && c.secondary)
  pinned.value = {
    co_duty_min_weight: (b.week || {}).co_duty_min_weight ?? 0,
    pairs, dualCells: pairs.length, degraded,
  }
}
async function save() {
  err.value = ''; saved.value = false
  try {
    await api('/settings', {
      method: 'PUT',
      body: JSON.stringify({ household: household.value, co_duty_min_weight: coDutyMinWeight.value }),
    })
    saved.value = true
  } catch (e) { err.value = e.message }
}
onMounted(load)
</script>
