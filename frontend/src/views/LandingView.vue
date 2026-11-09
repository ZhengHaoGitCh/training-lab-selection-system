<template>
  <div class="landing">
    <section class="hero">
      <div class="hero__inner">
        <div class="hero__copy">
          <div class="eyebrow">双向选择 · 分轮录取 · 统筹调剂</div>
          <h1>学生实训室<br />选组选拔系统</h1>
          <p>
            从集中宣讲、平行志愿填报，到统一面试、拟录取确认、分轮补录与统筹调剂——
            全流程线上协同，每一次改分、确认与调剂都留痕可查。
          </p>
          <div class="hero-actions">
            <el-button type="primary" size="large" @click="primaryAction">
              {{ auth.isLoggedIn ? '进入我的工作台' : '登录开始填报' }}
            </el-button>
            <el-button size="large" @click="$router.push('/announcements')">查看公示公告</el-button>
          </div>
          <div class="hero__facts">
            <div v-for="fact in facts" :key="fact.label">
              <strong class="num">{{ fact.value }}</strong>
              <span>{{ fact.label }}</span>
            </div>
          </div>
        </div>

        <div class="hero__panel">
          <div class="hero__panel-head">
            <span class="pill pill--navy">当前安排</span>
            <span class="muted">数据来自实时接口</span>
          </div>
          <RoundWindow v-if="focusRound" :round="focusRound" />
          <div v-else class="muted">暂无开放或即将开始的轮次</div>
          <div class="hero__panel-line"></div>
          <div class="hero__lab">
            <span class="muted">实训室开放日</span>
            <strong v-if="labs[0]?.open_day_at">{{ fmtDateTime(labs[0].open_day_at) }}</strong>
            <strong v-else>以学院通知为准</strong>
          </div>
          <div class="hero__panel-note">
            演示账号：学生 <code>2023001</code> · 老师 <code>t1001</code> · 管理员 <code>admin</code>
          </div>
        </div>
      </div>
    </section>

    <div class="page landing__body" v-loading="loading">
      <section class="section">
        <div class="section-head">
          <div>
            <h2>选拔流程总览</h2>
            <p>8 个阶段对应系统内 8 类轮次；时间以服务端轮次配置为准，海报日期仅作节奏参考。</p>
          </div>
          <span class="pill pill--blue">3 种角色协同</span>
        </div>
        <ProcessFlow />
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>实训室与导师名额</h2>
            <p>每个实训室下设多位导师，导师名额合计不超过实训室容量；剩余名额实时更新。</p>
          </div>
          <el-button text type="primary" @click="$router.push(auth.isLoggedIn && auth.isStudent ? '/student/intentions' : '/login')">
            去填报志愿 →
          </el-button>
        </div>
        <div v-if="labs.length" class="grid grid-3">
          <article v-for="lab in labs" :key="lab.id" class="card lab-card">
            <div class="lab-card__head">
              <span class="pill pill--blue">{{ lab.direction || '综合方向' }}</span>
              <span class="muted num">容量 {{ lab.capacity }}</span>
            </div>
            <h3>{{ lab.name }}</h3>
            <p class="lab-card__desc">{{ lab.description || '项目方向与培养安排以宣讲会为准。' }}</p>
            <div class="lab-card__mentors">
              <div v-for="mentor in lab.mentors" :key="mentor.id" class="mentor-row">
                <div class="mentor-row__info">
                  <strong>{{ mentor.name }}</strong>
                  <span class="muted">{{ mentor.requirement || '要求以导师说明为准' }}</span>
                </div>
                <div class="mentor-row__quota">
                  <span class="num">{{ mentor.quota_left }}/{{ mentor.quota }}</span>
                  <small>剩余</small>
                </div>
              </div>
            </div>
            <div v-if="lab.open_day_at" class="lab-card__foot muted">
              开放日：{{ fmtDateTime(lab.open_day_at) }}
            </div>
          </article>
        </div>
        <el-empty v-else description="暂无实训室数据，请先运行种子脚本" />
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>轮次时间表</h2>
            <p>进行中的轮次会高亮显示；学生只能在开放窗口内提交或修改志愿。</p>
          </div>
        </div>
        <div class="grid grid-3">
          <article
            v-for="round in rounds"
            :key="round.id"
            class="card round-card"
            :class="{ 'round-card--open': round.is_open }"
          >
            <div class="row">
              <StatusTag kind="roundKind" :value="round.kind" />
              <span class="spacer"></span>
              <span class="round-card__state" :class="`is-${roundState(round).key}`">
                {{ roundState(round).text }}
              </span>
            </div>
            <h3>{{ round.name }}</h3>
            <span class="time-badge num">
              {{ fmtDateTime(round.starts_at) }} ~ {{ fmtDateTime(round.ends_at) }}
            </span>
          </article>
        </div>
        <el-empty v-if="!rounds.length" description="暂无轮次" />
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>最新公示</h2>
            <p>公示期为 1 天，公示期间可实名提出异议。</p>
          </div>
          <el-button text type="primary" @click="$router.push('/announcements')">全部公示 →</el-button>
        </div>
        <div v-if="publications.length" class="grid grid-2">
          <article
            v-for="item in publications.slice(0, 4)"
            :key="item.id"
            class="card notice-card"
            @click="openPublication(item)"
          >
            <div class="row">
              <span class="pill pill--green">已发布</span>
              <span class="spacer"></span>
              <span class="muted num">{{ fmtDateTime(item.published_at) }}</span>
            </div>
            <h3>{{ item.title }}</h3>
            <p class="notice-card__content">{{ item.content || '点击查看公示正文' }}</p>
          </article>
        </div>
        <el-empty v-else description="暂无已发布公示" />
      </section>
    </div>

    <el-dialog v-model="dialogVisible" :title="activePublication?.title" width="min(640px, 92vw)">
      <div class="notice-dialog">
        <p class="muted num">发布于 {{ fmtDateTime(activePublication?.published_at) }}</p>
        <p class="notice-dialog__body">{{ activePublication?.content || '暂无正文' }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { metaApi } from '../api'
import ProcessFlow from '../components/ProcessFlow.vue'
import RoundWindow from '../components/RoundWindow.vue'
import StatusTag from '../components/StatusTag.vue'
import { useAuthStore } from '../stores/auth'
import { fmtDateTime, parseServerTime, roundState } from '../utils/format'

const auth = useAuthStore()
const router = useRouter()

const labs = ref([])
const rounds = ref([])
const publications = ref([])
const loading = ref(true)
const dialogVisible = ref(false)
const activePublication = ref(null)

const mentorCount = computed(() => labs.value.reduce((sum, lab) => sum + (lab.mentors?.length || 0), 0))
const quotaTotal = computed(() =>
  labs.value.reduce(
    (sum, lab) => sum + (lab.mentors || []).reduce((inner, mentor) => inner + Number(mentor.quota || 0), 0),
    0,
  ),
)
const openRounds = computed(() => rounds.value.filter((round) => round.is_open))
const focusRound = computed(() => {
  if (openRounds.value.length) return openRounds.value[0]
  const now = Date.now()
  return (
    rounds.value.find((round) => (parseServerTime(round.starts_at)?.getTime() ?? 0) > now) ||
    rounds.value[rounds.value.length - 1] ||
    null
  )
})

const facts = computed(() => [
  { label: '实训室', value: labs.value.length },
  { label: '导师', value: mentorCount.value },
  { label: '名额', value: quotaTotal.value },
  { label: '开放轮次', value: openRounds.value.length },
])

function primaryAction() {
  router.push(auth.isLoggedIn ? auth.homePath : '/login')
}

function openPublication(item) {
  activePublication.value = item
  dialogVisible.value = true
}

onMounted(async () => {
  try {
    const [labData, roundData, publicationData] = await Promise.all([
      metaApi.labs(),
      metaApi.rounds(),
      metaApi.publications(),
    ])
    labs.value = labData
    rounds.value = roundData
    publications.value = publicationData
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.hero {
  position: relative;
  overflow: hidden;
  border-bottom: 1px solid rgba(223, 230, 242, 0.9);
  background:
    radial-gradient(720px 340px at 82% 8%, rgba(232, 119, 46, 0.1), transparent 62%),
    radial-gradient(820px 420px at 6% 0%, rgba(124, 111, 186, 0.2), transparent 58%),
    linear-gradient(180deg, #f7f9fe 0%, #eef2fb 100%);
}

.hero::after {
  content: '';
  position: absolute;
  right: -80px;
  bottom: -120px;
  width: 380px;
  height: 380px;
  border-radius: 50%;
  border: 36px solid rgba(47, 111, 186, 0.06);
}

.hero__inner {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr);
  gap: 40px;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  padding: 64px 24px 52px;
}

.hero__copy h1 {
  margin-top: 12px;
  font-size: clamp(32px, 4.6vw, 54px);
  line-height: 1.12;
  letter-spacing: 0.01em;
}

.hero__copy p {
  margin-top: 18px;
  max-width: 620px;
  color: var(--tls-ink-soft);
  font-size: 15px;
  line-height: 1.9;
}

.hero-actions {
  margin-top: 26px;
}

.hero__facts {
  display: flex;
  flex-wrap: wrap;
  gap: 28px;
  margin-top: 34px;
}

.hero__facts div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.hero__facts strong {
  font-size: 26px;
  font-weight: 800;
  color: var(--tls-ink);
}

.hero__facts span {
  color: var(--tls-muted);
  font-size: 12px;
}

.hero__panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 22px;
  border: 1px solid #dbe4f3;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: 0 24px 56px rgba(23, 50, 77, 0.1);
  backdrop-filter: blur(10px);
}

.hero__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
}

.hero__panel-line {
  height: 1px;
  background: var(--tls-line);
}

.hero__lab {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
}

.hero__lab strong.num {
  font-size: 13px;
  color: var(--tls-ink-soft);
}

.hero__panel-note {
  padding: 10px 12px;
  border-radius: 10px;
  background: #f2f6fd;
  color: var(--tls-muted);
  font-size: 12px;
  line-height: 1.7;
}

.hero__panel-note code {
  color: var(--tls-primary-dark);
  font-weight: 700;
}

.landing__body {
  padding-top: 8px;
}

.lab-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.lab-card h3 {
  margin-top: 12px;
  font-size: 18px;
}

.lab-card__desc {
  margin-top: 8px;
  min-height: 44px;
  color: var(--tls-muted);
  font-size: 13px;
  line-height: 1.7;
}

.lab-card__mentors {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 14px;
}

.mentor-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f7f9fd;
  border: 1px solid #e8eef8;
}

.mentor-row__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.mentor-row__info strong {
  font-size: 13.5px;
}

.mentor-row__info span {
  overflow: hidden;
  color: var(--tls-muted);
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mentor-row__quota {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  flex-shrink: 0;
}

.mentor-row__quota span {
  color: var(--tls-primary-dark);
  font-size: 15px;
  font-weight: 800;
}

.mentor-row__quota small {
  color: var(--tls-muted);
  font-size: 10px;
}

.lab-card__foot {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--tls-line);
  font-size: 12px;
}

.round-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.round-card h3 {
  font-size: 15px;
}

.round-card--open {
  border-color: #b9d2ee;
  box-shadow: 0 14px 34px rgba(47, 111, 186, 0.13);
  background: linear-gradient(180deg, #fff 0%, #f4f9ff 100%);
}

.round-card__state {
  font-size: 12px;
  font-weight: 700;
  color: var(--tls-muted);
}

.round-card__state.is-open {
  color: var(--tls-green);
}

.round-card__state.is-upcoming {
  color: var(--tls-accent);
}

.notice-card {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.notice-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 38px rgba(23, 50, 77, 0.1);
}

.notice-card h3 {
  margin-top: 12px;
  font-size: 16px;
}

.notice-card__content {
  margin-top: 8px;
  display: -webkit-box;
  overflow: hidden;
  color: var(--tls-muted);
  font-size: 13px;
  line-height: 1.7;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.notice-dialog__body {
  margin-top: 10px;
  color: var(--tls-ink-soft);
  line-height: 1.9;
  white-space: pre-wrap;
}

@media (max-width: 980px) {
  .hero__inner {
    grid-template-columns: 1fr;
    padding: 44px 20px 40px;
  }

  .hero__panel {
    max-width: 520px;
  }
}

@media (max-width: 620px) {
  .hero__facts {
    gap: 18px;
  }

  .hero__facts strong {
    font-size: 22px;
  }
}
</style>
