<template>
  <div>
    <h1 class="brand">设置</h1>
    <label>家庭名 <input v-model="household" /></label>
    <label>
      双人同格阈值 co_duty_min_weight
      <input v-model="coDutyMinWeight" inputmode="numeric" placeholder="0" />
    </label>
    <p class="muted">
      0 = 关闭(单人一格);&gt;0 时 weight ≥ 阈值的重活每日分主/副两人。
      活跃成员不足两人时该任务当日自动降级单人并打「降级」标记。
      阈值只影响之后的生成,不会拆动已生成周的双人格。
    </p>
    <button @click="save">保存</button>
    <p v-if="err" class="err">{{ err }}</p>
    <p v-if="saved" class="muted">已保存</p>

    <h2>本周已钉配置</h2>
    <p v-if="pinned.co_duty_min_weight == null" class="muted">本周尚未生成,无钉住配置。</p>
    <template v-else>
      <p class="muted">
        生成时钉住阈值:{{ pinned.co_duty_min_weight }}
        <span v-if="pinned.co_duty_min_weight <= 0">(双人关闭)</span>
      </p>
      <p class="muted">
        主 {{ pinned.primary }} 格 · 副 {{ pinned.secondary }} 格 · 降级 {{ pinned.degraded }} 格
      </p>
    </template>

    <p class="muted" style="margin-top:16px">健康检查:{{ health }}</p>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const household = ref('')
const coDutyMinWeight = ref('0')
const health = ref('')
const err = ref('')
const saved = ref(false)
const pinned = ref({})
async function load() {
  const s = await api('/settings')
  household.value = s.household || ''
  coDutyMinWeight.value = s.co_duty_min_weight ?? '0'
  const h = await api('/health'); health.value = JSON.stringify(h)
  // 与看板同一数据源回看本周钉住的阈值与主/副/降级统计
  const b = await api('/weeks/1/board')
  const a = b.assignments || []
  pinned.value = {
    co_duty_min_weight: b.week?.co_duty_min_weight ?? null,
    primary: a.filter(x => x.role === 'primary').length,
    secondary: a.filter(x => x.role === 'secondary').length,
    degraded: a.filter(x => x.degraded).length,
  }
}
async function save() {
  err.value = ''; saved.value = false
  try {
    await api('/settings', { method: 'PUT', body: JSON.stringify({
      household: household.value,
      co_duty_min_weight: coDutyMinWeight.value,
    }) })
    saved.value = true
  } catch (e) { err.value = e.message }
}
onMounted(load)
</script>
