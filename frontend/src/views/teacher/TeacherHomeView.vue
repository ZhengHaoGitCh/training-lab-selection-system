<template>
  <div class="page" v-loading="loading">
    <PageHeader
      :title="`${auth.displayName}老师，你好`"
      subtitle="这里只展示你名下的报名学生、面试评分与录取情况；名额与名单由服务端实时计算。"
      eyebrow="Teacher"
    >
      <el-button type="primary" @click="$router.push('/teacher/applicants')">去评分</el-button>
    </PageHeader>

    <div v-if="profile" class="grid grid-2">
      <div class="card profile-card">
        <div class="profile-card__head">
          <span class="profile-card__avatar">{{ profile.mentor.name.slice(0, 1) }}</span>
          <div>
            <h3>{{ profile.mentor.name }}</h3>
            <p class="muted">{{ profile.lab?.name || '未绑定实训室' }}</p>
          </div>
          <span class="spacer"></span>
          <span class="pill" :class="profile.mentor.is_active ? 'pill--green' : 'pill--muted'">
            {{ profile.mentor.is_active ? '在招' : '已停用' }}
          </span>
        </div>
        <div class="profile-card__meta">
          <div><span class="muted">项目方向</span><strong>{{ profile.lab?.direction || '—' }}</strong></div>
          <div><span class="muted">实训室容量</span><strong class="num">{{ profile.lab?.capacity ?? '—' }}</strong></div>
          <div><span class="muted">考核要求</span><strong>{{ profile.mentor.requirement || '以导师说明为准' }}</strong></div>
        </div>
      </div>

      <div class="card quota-card">
        <div class="card-title">
          <h3>名额使用情况</h3>
          <span class="muted num">{{ profile.quota_taken }} / {{ profile.mentor.quota }}</span>
        </div>
        <el-progress
          :percentage="quotaPercent(profile.quota_taken, profile.mentor.quota)"
          :stroke-width="12"
          :color="progressColor"
        />
        <div class="quota-card__nums">
          <div>
            <span class="muted">剩余名额</span>
            <strong class="num">{{ profile.quota_left }}</strong>
          </div>
          <div>
            <span class="muted">待确认</span>
            <strong class="num">{{ profile.counts.offers_pending }}</strong>
          </div>
          <div>
            <span class="muted">已确认</span>
            <strong class="num">{{ profile.counts.offers_confirmed }}</strong>
          </div>
        </div>
        <el-button text type="primary" @click="$router.push('/teacher/offers')">查看我的名单 →</el-button>
      </div>
    </div>

    <section class="section">
      <div class="stat-grid">
        <StatCard label="报名学生" :value="profile?.counts.applicants ?? 0" suffix="人" tone="blue" hint="填报了你的志愿" />
        <StatCard label="已面试" :value="profile?.counts.interviewed ?? 0" suffix="人" tone="orange" hint="已完成四维评分" />
        <StatCard label="待确认" :value="profile?.counts.offers_pending ?? 0" suffix="个" tone="green" hint="等待学生在窗口内确认" />
        <StatCard label="已确认" :value="profile?.counts.offers_confirmed ?? 0" suffix="人" tone="navy" hint="正式入组" />
      </div>
    </section>

    <section class="section grid grid-2">
      <div class="card">
        <div class="card-title">
          <h3>待办</h3>
        </div>
        <div class="quick-list">
          <router-link to="/teacher/applicants" class="quick-item">
            <span class="quick-item__index">01</span>
            <div>
              <strong>报名学生与评分</strong>
              <small>按学习态度、逻辑、编程基础、时间投入打分</small>
            </div>
          </router-link>
          <router-link to="/teacher/offers" class="quick-item">
            <span class="quick-item__index">02</span>
            <div>
              <strong>我的录取名单</strong>
              <small>查看拟录取、递补、调剂与学生确认状态</small>
            </div>
          </router-link>
        </div>
        <div class="callout" style="margin-top: 14px">
          评分维度：学习态度与动机 25 + 逻辑思维与表达 20 + 编程/专业基础 35 + 时间投入与协作 20，总分 100。
        </div>
      </div>

      <div class="card">
        <div class="card-title">
          <h3>本轮次提示</h3>
          <span class="muted">来自服务端</span>
        </div>
        <RoundWindow :round="focusRound" />
        <div class="round-list">
          <div v-for="round in rounds" :key="round.id" class="round-item" :class="{ 'is-open': round.is_open }">
            <StatusTag kind="roundKind" :value="round.kind" />
            <span class="round-item__name">{{ round.name }}</span>
            <span class="muted num">{{ fmtDateTime(round.starts_at) }}</span>
          </div>
        </div>
        <el-empty v-if="!rounds.length" description="暂无轮次" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { metaApi, teacherApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import RoundWindow from '../../components/RoundWindow.vue'
import StatCard from '../../components/StatCard.vue'
import StatusTag from '../../components/StatusTag.vue'
import { useAuthStore } from '../../stores/auth'
import { fmtDateTime, parseServerTime, quotaPercent } from '../../utils/format'

const auth = useAuthStore()
const loading = ref(true)
const profile = ref(null)
const rounds = ref([])

const focusRound = computed(() => {
  const open = rounds.value.find((round) => round.is_open)
  if (open) return open
  const now = Date.now()
  return (
    rounds.value.find((round) => (parseServerTime(round.starts_at)?.getTime() ?? 0) > now) ||
    rounds.value[rounds.value.length - 1] ||
    null
  )
})

const progressColor = computed(() => {
  const percent = quotaPercent(profile.value?.quota_taken || 0, profile.value?.mentor?.quota || 0)
  if (percent >= 100) return '#e8772e'
  if (percent >= 70) return '#2f6fba'
  return '#1f7a5c'
})

onMounted(async () => {
  try {
    const [profileData, roundData] = await Promise.all([teacherApi.profile(), metaApi.rounds()])
    profile.value = profileData
    rounds.value = roundData
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.profile-card__head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.profile-card__avatar {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: linear-gradient(145deg, #17324d, #2f6fba);
  color: #fff;
  font-size: 18px;
  font-weight: 800;
}

.profile-card__head h3 {
  font-size: 18px;
}

.profile-card__head p {
  margin-top: 2px;
  font-size: 12.5px;
}

.profile-card__meta {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.profile-card__meta div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.profile-card__meta span {
  font-size: 11.5px;
}

.profile-card__meta strong {
  font-size: 13px;
  font-weight: 600;
  color: var(--tls-ink-soft);
  line-height: 1.6;
}

.quota-card__nums {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 16px 0 10px;
}

.quota-card__nums div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f6f9fd;
}

.quota-card__nums span {
  font-size: 11.5px;
}

.quota-card__nums strong {
  font-size: 20px;
  font-weight: 800;
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

.round-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 14px;
}

.round-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 8px;
  font-size: 12px;
}

.round-item.is-open {
  background: #f2f9f5;
}

.round-item__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--tls-ink-soft);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .quota-card__nums {
    grid-template-columns: 1fr;
  }
}
</style>
