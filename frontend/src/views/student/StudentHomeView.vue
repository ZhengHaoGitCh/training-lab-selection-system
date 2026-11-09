<template>
  <div class="page" v-loading="loading">
    <PageHeader
      :title="`你好，${auth.displayName}`"
      subtitle="这里汇总你的选组阶段、轮次安排与待办事项。所有状态以服务端为准。"
      eyebrow="Student"
    >
      <StatusTag kind="stage" :value="status.stage" />
    </PageHeader>

    <div v-if="status.stage === 'enrolled'" class="callout callout--success">
      你已确认入组：<strong>{{ status.final_lab }}</strong> · {{ status.final_mentor }}。
      请按学院通知参加后续实训。
    </div>
    <div v-else-if="status.stage === 'not_applied'" class="callout callout--orange">
      你还没有填报志愿。请在“志愿填报”中选择最多 3 个平行导师意向，并设置是否服从调剂。
    </div>

    <section class="section">
      <div class="stat-grid">
        <StatCard label="我的志愿" :value="status.intentions" suffix="个" tone="blue" hint="最多 3 个，不分先后" />
        <StatCard label="面试记录" :value="status.interviews" suffix="条" tone="orange" hint="由老师统一评分" />
        <StatCard label="待确认拟录取" :value="status.pending_offers" suffix="个" tone="green" hint="逾期视为放弃" />
        <StatCard
          label="调剂意愿"
          :value="status.obey_internal || status.obey_cross ? '已开启' : '未开启'"
          tone="navy"
          :hint="obeyHint"
        />
      </div>
    </section>

    <section class="section grid grid-2">
      <div class="card">
        <div class="card-title">
          <h3>当前轮次</h3>
          <router-link to="/student/intentions" class="link-more">去填报 →</router-link>
        </div>
        <RoundWindow :round="focusRound" />
        <div class="callout" style="margin-top: 14px">
          志愿提交前请确认导师名额与考核要求；截止后志愿锁定。
          系统故障时以操作日志与时间戳复核。
        </div>
      </div>

      <div class="card">
        <div class="card-title">
          <h3>下一步</h3>
        </div>
        <div class="quick-list">
          <router-link to="/student/intentions" class="quick-item">
            <span class="quick-item__index">01</span>
            <div>
              <strong>填报 / 修改志愿</strong>
              <small>查看实训室与导师剩余名额</small>
            </div>
          </router-link>
          <router-link to="/student/offers" class="quick-item">
            <span class="quick-item__index">02</span>
            <div>
              <strong>查看拟录取并确认</strong>
              <small>唯一去向确认后不可更改</small>
            </div>
          </router-link>
          <router-link to="/student/appeals" class="quick-item">
            <span class="quick-item__index">03</span>
            <div>
              <strong>实名申诉</strong>
              <small>对公示结果提出异议并查看回复</small>
            </div>
          </router-link>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <div class="card-title">
          <h3>轮次时间轴</h3>
          <span class="muted">共 {{ schedule.length }} 个阶段</span>
        </div>
        <div class="timeline">
          <div v-for="round in schedule" :key="round.id" class="timeline__item" :class="{ 'is-open': round.is_open }">
            <div class="timeline__dot"></div>
            <div class="timeline__body">
              <div class="row">
                <StatusTag kind="roundKind" :value="round.kind" />
                <strong>{{ round.name }}</strong>
                <span class="spacer"></span>
                <span class="timeline__state" :class="`is-${roundState(round).key}`">{{ roundState(round).text }}</span>
              </div>
              <div class="muted num timeline__time">
                {{ fmtDateTime(round.starts_at) }} ~ {{ fmtDateTime(round.ends_at) }}
              </div>
            </div>
          </div>
        </div>
        <el-empty v-if="!schedule.length" description="暂无轮次安排" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { studentApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import RoundWindow from '../../components/RoundWindow.vue'
import StatCard from '../../components/StatCard.vue'
import StatusTag from '../../components/StatusTag.vue'
import { useAuthStore } from '../../stores/auth'
import { fmtDateTime, parseServerTime, roundState } from '../../utils/format'

const auth = useAuthStore()
const loading = ref(true)
const status = ref({
  stage: 'not_applied',
  intentions: 0,
  interviews: 0,
  pending_offers: 0,
  obey_internal: false,
  obey_cross: false,
  final_mentor: null,
  final_lab: null,
})
const schedule = ref([])

const focusRound = computed(() => {
  const open = schedule.value.find((round) => round.is_open)
  if (open) return open
  const now = Date.now()
  return (
    schedule.value.find((round) => (parseServerTime(round.starts_at)?.getTime() ?? 0) > now) ||
    schedule.value[schedule.value.length - 1] ||
    null
  )
})

const obeyHint = computed(() => {
  if (status.value.obey_internal && status.value.obey_cross) return '内部 + 全院跨室'
  if (status.value.obey_internal) return '仅实训室内部'
  if (status.value.obey_cross) return '仅全院跨室'
  return '可在填报时设置'
})

onMounted(async () => {
  try {
    const [statusData, scheduleData] = await Promise.all([studentApi.status(), studentApi.schedule()])
    status.value = statusData
    schedule.value = scheduleData
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.callout--success {
  border-color: var(--tls-green);
  background: var(--tls-green-soft);
  color: #175f48;
}

.link-more {
  font-size: 12.5px;
  font-weight: 600;
}

.quick-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quick-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border: 1px solid var(--tls-line);
  border-radius: 12px;
  background: #f9fbff;
  transition: all 0.16s ease;
}

.quick-item:hover {
  border-color: #b9d2ee;
  background: #f2f8ff;
  transform: translateX(2px);
}

.quick-item__index {
  color: #b9c9de;
  font-size: 18px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.quick-item div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.quick-item strong {
  color: var(--tls-ink);
  font-size: 13.5px;
}

.quick-item small {
  color: var(--tls-muted);
  font-size: 11.5px;
}

.timeline {
  display: flex;
  flex-direction: column;
}

.timeline__item {
  display: grid;
  grid-template-columns: 18px 1fr;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed #e8eef8;
}

.timeline__item:last-child {
  border-bottom: none;
}

.timeline__dot {
  position: relative;
  width: 10px;
  height: 10px;
  margin-top: 8px;
  border-radius: 50%;
  background: #c7d5e8;
  justify-self: center;
}

.timeline__item.is-open .timeline__dot {
  background: var(--tls-green);
  box-shadow: 0 0 0 4px rgba(31, 122, 92, 0.14);
}

.timeline__state {
  color: var(--tls-muted);
  font-size: 12px;
  font-weight: 700;
}

.timeline__state.is-open {
  color: var(--tls-green);
}

.timeline__state.is-upcoming {
  color: var(--tls-accent);
}

.timeline__time {
  margin-top: 4px;
  font-size: 12px;
}

@media (max-width: 620px) {
  .timeline__body .row {
    align-items: flex-start;
  }

  .timeline__state {
    width: 100%;
  }
}
</style>
