<template>
  <div>
    <h1 class="brand">本周看板</h1>
    <p class="muted">
      周卡片网格 · round-robin 落位后可去「对调」申请交换
      <template v-if="week.co_duty_min_weight != null">
        · 双人阈值已钉:weight ≥ {{ week.co_duty_min_weight }}
        <span v-if="week.co_duty_min_weight <= 0">(本周生成时双人关闭)</span>
      </template>
    </p>
    <div style="display:flex;gap:8px;margin:12px 0">
      <button @click="generate">生成周表</button>
      <button class="ghost" @click="load">刷新</button>
    </div>
    <p v-if="err" class="err">{{ err }}</p>
    <div class="week-grid">
      <article v-for="d in days" :key="d" class="week-card">
        <header>Day {{ d }}</header>
        <div v-for="g in groupsFor(d)" :key="g.task_id">
          <span class="chip">{{ g.task_title }}</span>
          <span v-for="s in g.slots" :key="s.id" class="chip coral">
            <b v-if="s.role === 'primary'" class="role">主</b>
            <b v-else-if="s.role === 'secondary'" class="role">副</b>
            {{ s.member_name }}
            <em v-if="s.degraded" class="degraded">降级</em>
          </span>
        </div>
        <p v-if="!groupsFor(d).length" class="muted">空</p>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const assigns = ref([])
const week = ref({})
const days = [0,1,2,3,4,5,6]
const err = ref('')
const weekId = 1
// 同日同任务聚成一格:双人任务一行两 chip(主/副),降级单人带「降级」标记
function groupsFor(d) {
  const byTask = new Map()
  for (const a of assigns.value.filter(a => a.day === d)) {
    if (!byTask.has(a.task_id)) byTask.set(a.task_id, { task_id: a.task_id, task_title: a.task_title, slots: [] })
    byTask.get(a.task_id).slots.push(a)
  }
  return [...byTask.values()]
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
