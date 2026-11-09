<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="面试评分"
      subtitle="管理员可代录或校正任意学生的四维评分；老师只能给填报了自己志愿的学生评分。修改会写入审计日志。"
      eyebrow="Admin / Interviews"
    >
      <el-button type="primary" @click="openDialog()">代录评分</el-button>
    </PageHeader>

    <div class="card toolbar">
      <el-select v-model="filterRound" placeholder="全部轮次" clearable style="width: 200px" @change="load">
        <el-option v-for="round in rounds" :key="round.id" :label="round.name" :value="round.id" />
      </el-select>
      <el-select v-model="filterMentor" placeholder="全部导师" clearable style="width: 180px" @change="load">
        <el-option v-for="mentor in mentors" :key="mentor.id" :label="mentor.name" :value="mentor.id" />
      </el-select>
      <span class="spacer"></span>
      <span class="muted num">共 {{ interviews.length }} 条</span>
    </div>

    <div class="card">
      <div class="table-wrap">
        <el-table :data="interviews" row-key="id" stripe>
          <el-table-column label="学生" min-width="140">
            <template #default="{ row }">
              <strong>{{ row.student_name }}</strong>
              <div class="muted num">{{ row.student_no }}</div>
            </template>
          </el-table-column>
          <el-table-column label="导师" min-width="110" prop="mentor_name" />
          <el-table-column label="轮次" min-width="130">
            <template #default="{ row }">{{ roundName(row.round_id) }}</template>
          </el-table-column>
          <el-table-column label="四维得分" min-width="220">
            <template #default="{ row }">
              <div class="score-detail num">
                态度 {{ row.score_attitude }}/25 · 逻辑 {{ row.score_logic }}/20
              </div>
              <div class="score-detail num">
                编程 {{ row.score_code }}/35 · 投入 {{ row.score_time }}/20
              </div>
            </template>
          </el-table-column>
          <el-table-column label="总分" width="90">
            <template #default="{ row }">
              <strong class="total num">{{ row.total_score }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="结论" width="130">
            <template #default="{ row }"><StatusTag kind="decision" :value="row.decision" /></template>
          </el-table-column>
          <el-table-column label="评语" min-width="160" prop="remark" show-overflow-tooltip />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-if="!interviews.length && !loading" description="暂无面试记录" />
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑面试评分' : '代录面试评分'" width="min(600px, 94vw)">
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="学生">
            <el-select v-model="form.student_id" filterable :disabled="Boolean(editing)" style="width: 100%">
              <el-option
                v-for="student in students"
                :key="student.id"
                :label="`${student.name}（${student.student_no}）`"
                :value="student.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="导师">
            <el-select v-model="form.mentor_id" filterable :disabled="Boolean(editing)" style="width: 100%">
              <el-option
                v-for="mentor in mentors"
                :key="mentor.id"
                :label="`${mentor.name} · ${mentor.lab_name}`"
                :value="mentor.id"
              />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="面试轮次">
          <el-select v-model="form.round_id" :disabled="Boolean(editing)" style="width: 100%">
            <el-option v-for="round in rounds" :key="round.id" :label="round.name" :value="round.id" />
          </el-select>
        </el-form-item>

        <div class="score-head">
          <span class="muted">评分维度固定上限，总分实时计算</span>
          <div class="score-total">
            <span>总分</span>
            <strong class="num">{{ formTotal }}</strong>
            <span>/ 100</span>
          </div>
        </div>
        <div class="dimension-grid">
          <el-form-item v-for="dim in dimensions" :key="dim.key" :label="`${dim.label}（0–${dim.max}）`">
            <el-input-number v-model="form[dim.key]" :min="0" :max="dim.max" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="评语">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'

const loading = ref(true)
const saving = ref(false)
const rounds = ref([])
const mentors = ref([])
const students = ref([])
const interviews = ref([])
const filterRound = ref(null)
const filterMentor = ref(null)
const dialogVisible = ref(false)
const editing = ref(null)

const dimensions = [
  { key: 'score_attitude', label: '学习态度与动机', max: 25 },
  { key: 'score_logic', label: '逻辑思维与表达', max: 20 },
  { key: 'score_code', label: '编程 / 专业基础', max: 35 },
  { key: 'score_time', label: '时间投入与协作', max: 20 },
]

const form = reactive({
  student_id: null,
  mentor_id: null,
  round_id: null,
  score_attitude: 0,
  score_logic: 0,
  score_code: 0,
  score_time: 0,
  remark: '',
})

const formTotal = computed(
  () =>
    Number(form.score_attitude || 0) +
    Number(form.score_logic || 0) +
    Number(form.score_code || 0) +
    Number(form.score_time || 0),
)

function roundName(id) {
  return rounds.value.find((round) => round.id === id)?.name || `轮次 ${id}`
}

function openDialog(row = null) {
  editing.value = row
  Object.assign(form, {
    student_id: row?.student_id ?? students.value[0]?.id ?? null,
    mentor_id: row?.mentor_id ?? mentors.value[0]?.id ?? null,
    round_id: row?.round_id ?? rounds.value.find((round) => round.is_open)?.id ?? rounds.value[0]?.id ?? null,
    score_attitude: row?.score_attitude ?? 0,
    score_logic: row?.score_logic ?? 0,
    score_code: row?.score_code ?? 0,
    score_time: row?.score_time ?? 0,
    remark: row?.remark || '',
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.student_id || !form.mentor_id || !form.round_id) {
    ElMessage.warning('请选择学生、导师与轮次')
    return
  }
  saving.value = true
  try {
    await adminApi.saveInterview({ ...form })
    ElMessage.success('评分已保存')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function load() {
  const params = { limit: 500 }
  if (filterRound.value) params.round_id = filterRound.value
  if (filterMentor.value) params.mentor_id = filterMentor.value
  const data = await adminApi.interviews(params)
  interviews.value = data.items || []
}

onMounted(async () => {
  try {
    const [roundData, mentorData, studentData] = await Promise.all([
      adminApi.rounds(),
      adminApi.mentors(),
      adminApi.students({ limit: 500 }),
    ])
    rounds.value = roundData
    mentors.value = mentorData
    students.value = studentData.items || []
    await load()
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
  margin-bottom: 16px;
  padding: 14px 16px;
  flex-wrap: wrap;
}

.score-detail {
  color: var(--tls-muted);
  font-size: 11px;
  line-height: 1.5;
}

.total {
  color: var(--tls-primary-dark);
  font-size: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.dimension-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

.score-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
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
  font-size: 26px;
  font-weight: 800;
}

@media (max-width: 620px) {
  .form-grid,
  .dimension-grid {
    grid-template-columns: 1fr;
  }
}
</style>
