<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="报名学生"
      subtitle="只展示填报了你的志愿的学生。评分维度固定为 25 / 20 / 35 / 20，合计 100 分，可重复提交覆盖并留痕。"
      eyebrow="Applicants"
    >
      <span class="pill pill--blue">{{ rows.length }} 位报名学生</span>
    </PageHeader>

    <div class="stat-grid">
      <StatCard label="报名学生" :value="rows.length" suffix="人" tone="blue" />
      <StatCard label="已评分" :value="scoredCount" suffix="人" tone="green" />
      <StatCard label="未评分" :value="rows.length - scoredCount" suffix="人" tone="orange" />
      <StatCard label="已有录取记录" :value="offerCount" suffix="人" tone="navy" />
    </div>

    <div class="card toolbar">
      <el-input v-model="keyword" placeholder="搜索姓名或学号" clearable style="width: min(280px, 100%)">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filter" style="width: 160px">
        <el-option label="全部学生" value="all" />
        <el-option label="未评分" value="unscored" />
        <el-option label="已评分" value="scored" />
      </el-select>
      <span class="spacer"></span>
      <span class="muted">按最近一次评分与录取状态展示</span>
    </div>

    <div class="card">
      <div class="table-wrap">
        <el-table :data="filteredRows" row-key="student_id" stripe>
          <el-table-column label="学生" min-width="150">
            <template #default="{ row }">
              <div class="student-cell">
                <span class="student-cell__avatar">{{ row.student_name.slice(0, 1) }}</span>
                <div>
                  <strong>{{ row.student_name }}</strong>
                  <small class="num">{{ row.student_no }}</small>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="志愿轮次" min-width="140">
            <template #default="{ row }">
              <span>{{ roundName(row.intention_round_id) }}</span>
              <div class="muted num">第 {{ row.priority }} 志愿 · {{ fmtDateTime(row.intended_at) }}</div>
            </template>
          </el-table-column>
          <el-table-column label="调剂意愿" min-width="150">
            <template #default="{ row }">
              <div class="row">
                <span v-if="row.obey_internal" class="pill pill--blue">内部</span>
                <span v-if="row.obey_cross" class="pill pill--green">跨室</span>
                <span v-if="!row.obey_internal && !row.obey_cross" class="pill pill--muted">不服从</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="面试评分" min-width="190">
            <template #default="{ row }">
              <template v-if="row.interview">
                <div class="score-cell">
                  <strong class="num">{{ row.interview.total_score }}</strong>
                  <span>/ 100</span>
                  <StatusTag kind="decision" :value="row.interview.decision" />
                </div>
                <div class="muted score-detail num">
                  态度 {{ row.interview.score_attitude }} · 逻辑 {{ row.interview.score_logic }} ·
                  编程 {{ row.interview.score_code }} · 投入 {{ row.interview.score_time }}
                </div>
              </template>
              <span v-else class="pill pill--orange">未评分</span>
            </template>
          </el-table-column>
          <el-table-column label="录取状态" min-width="150">
            <template #default="{ row }">
              <template v-if="row.offer">
                <StatusTag kind="offerStatus" :value="row.offer.status" />
                <div class="muted offer-type">{{ OFFER_TYPE_TEXT[row.offer.offer_type] || row.offer.offer_type }}</div>
              </template>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="openScore(row)">
                {{ row.interview ? '修改评分' : '评分' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-if="!filteredRows.length && !loading" description="暂无报名学生" />
    </div>

    <el-dialog v-model="scoreVisible" :title="`面试评分 · ${activeRow?.student_name || ''}`" width="min(620px, 94vw)">
      <div class="score-head">
        <div>
          <div class="muted num">{{ activeRow?.student_no }}</div>
          <div class="muted">
            志愿轮次：{{ activeRow ? roundName(activeRow.intention_round_id) : '—' }}
          </div>
        </div>
        <div class="score-total">
          <span>总分</span>
          <strong class="num">{{ scoreTotal }}</strong>
          <span>/ 100</span>
        </div>
      </div>
      <el-progress :percentage="scoreTotal" :stroke-width="10" :show-text="false" :color="scoreColor" />

      <el-form label-position="top" class="score-form">
        <el-form-item label="面试轮次">
          <el-select v-model="scoreForm.round_id" placeholder="选择面试轮次" style="width: 100%">
            <el-option v-for="round in scoreRounds" :key="round.id" :label="round.name" :value="round.id" />
          </el-select>
        </el-form-item>
        <div class="dimension-grid">
          <el-form-item v-for="dim in dimensions" :key="dim.key" :label="`${dim.label}（0–${dim.max}）`">
            <el-input-number v-model="scoreForm[dim.key]" :min="0" :max="dim.max" :step="1" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="评语（可选）">
          <el-input v-model="scoreForm.remark" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="scoreVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveScore">保存评分</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { metaApi, teacherApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import StatCard from '../../components/StatCard.vue'
import StatusTag from '../../components/StatusTag.vue'
import { OFFER_TYPE_TEXT, fmtDateTime, parseServerTime } from '../../utils/format'

const loading = ref(true)
const saving = ref(false)
const rows = ref([])
const rounds = ref([])
const keyword = ref('')
const filter = ref('all')
const scoreVisible = ref(false)
const activeRow = ref(null)

const dimensions = [
  { key: 'score_attitude', label: '学习态度与动机', max: 25 },
  { key: 'score_logic', label: '逻辑思维与表达', max: 20 },
  { key: 'score_code', label: '编程 / 专业基础', max: 35 },
  { key: 'score_time', label: '时间投入与协作', max: 20 },
]

const scoreForm = reactive({
  student_id: null,
  round_id: null,
  score_attitude: 0,
  score_logic: 0,
  score_code: 0,
  score_time: 0,
  remark: '',
})

const scoreTotal = computed(
  () =>
    Number(scoreForm.score_attitude || 0) +
    Number(scoreForm.score_logic || 0) +
    Number(scoreForm.score_code || 0) +
    Number(scoreForm.score_time || 0),
)

const scoreColor = computed(() => {
  if (scoreTotal.value >= 75) return '#1f7a5c'
  if (scoreTotal.value >= 50) return '#2f6fba'
  return '#e8772e'
})

const scoredCount = computed(() => rows.value.filter((row) => row.interview).length)
const offerCount = computed(() => rows.value.filter((row) => row.offer).length)

const filteredRows = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return rows.value.filter((row) => {
    if (filter.value === 'scored' && !row.interview) return false
    if (filter.value === 'unscored' && row.interview) return false
    if (!text) return true
    return (
      row.student_name.toLowerCase().includes(text) ||
      row.student_no.toLowerCase().includes(text)
    )
  })
})

const scoreRounds = computed(() => {
  const interviewRounds = rounds.value.filter((round) => round.kind === 'interview')
  return interviewRounds.length ? interviewRounds : rounds.value
})

function defaultScoreRound() {
  const open = scoreRounds.value.find((round) => round.is_open)
  return open?.id || scoreRounds.value[scoreRounds.value.length - 1]?.id || null
}

function roundName(id) {
  return rounds.value.find((round) => round.id === id)?.name || `轮次 ${id}`
}

function openScore(row) {
  activeRow.value = row
  const existing = row.interview
  Object.assign(scoreForm, {
    student_id: row.student_id,
    round_id: existing?.round_id || defaultScoreRound(),
    score_attitude: existing?.score_attitude ?? 0,
    score_logic: existing?.score_logic ?? 0,
    score_code: existing?.score_code ?? 0,
    score_time: existing?.score_time ?? 0,
    remark: existing?.remark || '',
  })
  scoreVisible.value = true
}

async function saveScore() {
  if (!scoreForm.round_id) {
    ElMessage.warning('请选择面试轮次')
    return
  }
  saving.value = true
  try {
    await teacherApi.score({ ...scoreForm })
    ElMessage.success('评分已保存')
    scoreVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function load() {
  rows.value = await teacherApi.applicants()
}

onMounted(async () => {
  try {
    const [applicantData, roundData] = await Promise.all([teacherApi.applicants(), metaApi.rounds()])
    rows.value = applicantData
    rounds.value = roundData
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  padding: 14px 16px;
  flex-wrap: wrap;
}

.student-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.student-cell__avatar {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e8f0fb;
  color: var(--tls-primary-dark);
  font-size: 13px;
  font-weight: 800;
}

.student-cell div {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.student-cell strong {
  font-size: 13.5px;
}

.student-cell small {
  color: var(--tls-muted);
  font-size: 11.5px;
}

.score-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.score-cell strong {
  font-size: 18px;
  color: var(--tls-primary-dark);
}

.score-cell span {
  color: var(--tls-muted);
  font-size: 11px;
}

.score-detail {
  margin-top: 2px;
  font-size: 11px;
}

.offer-type {
  margin-top: 4px;
  font-size: 11px;
}

.score-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.score-head .muted {
  font-size: 12px;
}

.score-total {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.score-total span {
  color: var(--tls-muted);
  font-size: 12px;
}

.score-total strong {
  color: var(--tls-ink);
  font-size: 30px;
  font-weight: 800;
}

.score-form {
  margin-top: 18px;
}

.dimension-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

@media (max-width: 620px) {
  .dimension-grid {
    grid-template-columns: 1fr;
  }

  .score-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
