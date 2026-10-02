<template>
  <div>
    <h1 class="brand">本周看板</h1>
    <p class="muted">
      周卡片网格 · round-robin 落位后可去「对调」申请交换 ·
      双人同格阈值（本周已钉）：<b>{{ pinnedThreshold }}</b>
      <template v-if="pinnedThreshold > 0">（weight ≥ {{ pinnedThreshold }} 的重活主/副两人同格）</template>
      <template v-else>（0 = 关闭，单人一格）</template>
    </p>
    <div style="display:flex;gap:8px;margin:12px 0">
      <button @click="generate">生成周表</button>
      <button class="ghost" @click="load">刷新</button>
    </div>
    <p v-if="err" class="err">{{ err }}</p>
    <div class="week-grid">
      <article v-for="d in days" :key="d" class="week-card">
        <header>Day {{ d }}</header>
        <div v-for="cell in byDay(d)" :key="cell.task_id">
          <span class="chip">{{ cell.task_title }}</span>
          <span v-for="m in cell.members" :key="m.id"
                class="chip coral" :class="{ secondary: m.role === 'secondary' }">
            {{ m.member_name }}<i v-if="m.role === 'secondary'">·副</i>
          </span>
          <span v-if="cell.degraded" class="chip warn">降级单人</span>
        </div>
        <p v-if="!byDay(d).length" class="muted">空</p>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
const assigns = ref([])
const week = ref({})
const days = [0,1,2,3,4,5,6]
const err = ref('')
const weekId = 1
const pinnedThreshold = computed(() => week.value.co_duty_min_weight ?? 0)
// 同日同任务聚成一格：成员按落库序（主在前、副在后）
function byDay(d) {
  const cells = new Map()
  for (const a of assigns.value.filter(a => a.day === d)) {
    if (!cells.has(a.task_id)) {
      cells.set(a.task_id, { task_id: a.task_id, task_title: a.task_title, members: [], degraded: 0 })
    }
    const c = cells.get(a.task_id)
    c.members.push(a)
    c.degraded = c.degraded || a.degraded
  }
  return [...cells.values()]
}
async function load() {
  err.value = ''
  try {
    const b = await api('/weeks/' + weekId + '/board')
    assigns.value = b.assignments || []
    week.value = b.week || {}
  } catch (e) { err.value = e.message }
}
async function generate() {
  err.value = ''
  try { await api('/weeks/' + weekId + '/generate', { method: 'POST', body: '{}' }); await load() }
  catch (e) { err.value = e.message }
}
onMounted(load)
</script>
