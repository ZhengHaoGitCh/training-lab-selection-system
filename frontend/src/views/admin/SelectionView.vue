<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="选拔与录取"
      subtitle="运行选拔、逾期释放、顺位补录、统筹调剂与约谈安置。正式操作前建议先预演确认人数。"
      eyebrow="Admin / Selection"
    >
      <el-button @click="loadOffers">刷新名单</el-button>
    </PageHeader>

    <div v-if="!canAct" class="callout callout--orange" style="margin-bottom: 14px">
      当前角色为只读（监督），可以查看名单与预演结果，但不能执行正式选拔、补录、调剂或约谈安置。
    </div>

    <el-tabs v-model="activeTab" class="card tabs-card">
      <el-tab-pane label="运行选拔" name="run">
        <div class="pane-grid">
          <div class="card card--flat">
            <div class="card-title"><h3>执行一轮选拔</h3></div>
            <el-form label-position="top">
              <el-form-item label="轮次">
                <el-select v-model="runForm.round_id" placeholder="选择轮次" style="width: 100%">
                  <el-option v-for="round in rounds" :key="round.id" :label="round.name" :value="round.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="确认有效期（分钟）">
                <el-input-number v-model="runForm.confirm_minutes" :min="1" :max="10080" style="width: 100%" />
              </el-form-item>
              <el-form-item label="预演模式">
                <div class="row">
                  <el-switch v-model="runForm.dry_run" />
                  <span class="muted">{{ runForm.dry_run ? '预演：仅计算、不落库' : '正式：会生成拟录取记录' }}</span>
                </div>
              </el-form-item>
              <el-button type="primary" :disabled="!canAct" :loading="acting" @click="runSelection">
                {{ runForm.dry_run ? '运行预演' : '正式运行选拔' }}
              </el-button>
            </el-form>
            <div class="callout" style="margin-top: 14px">
              正式执行会按导师分别排序（总分降序、学号升序），生成待确认拟录取记录，并写入审计日志。
            </div>
          </div>

          <div class="card card--flat">
            <div class="card-title"><h3>预演 / 执行结果</h3></div>
            <template v-if="runResult">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="拟录取">{{ runResult.proposed }}</el-descriptions-item>
                <el-descriptions-item label="递补">{{ runResult.waitlist }}</el-descriptions-item>
                <el-descriptions-item label="内部调剂候选">{{ runResult.internal_candidate }}</el-descriptions-item>
                <el-descriptions-item label="不推荐">{{ runResult.rejected }}</el-descriptions-item>
                <el-descriptions-item label="新建拟录取">{{ runResult.offers_created }}</el-descriptions-item>
                <el-descriptions-item label="跳过">{{ runResult.offers_skipped }}</el-descriptions-item>
              </el-descriptions>
              <el-alert
                style="margin-top: 12px"
                :type="runResult.dry_run ? 'info' : 'success'"
                :closable="false"
                :title="runResult.dry_run ? '预演完成，未写入数据库' : '选拔完成，已生成待确认记录'"
              />
            </template>
            <el-empty v-else description="还没有执行结果" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="拟录取名单" name="offers">
        <div class="toolbar">
          <el-select v-model="offerRound" placeholder="全部轮次" clearable style="width: 170px" @change="loadOffers">
            <el-option v-for="round in rounds" :key="round.id" :label="round.name" :value="round.id" />
          </el-select>
          <el-select v-model="offerStatus" placeholder="全部状态" clearable style="width: 150px" @change="loadOffers">
            <el-option v-for="(label, status) in OFFER_STATUS_TEXT" :key="status" :label="label" :value="status" />
          </el-select>
          <el-select v-model="offerMentor" placeholder="全部导师" clearable style="width: 170px" @change="loadOffers">
            <el-option v-for="mentor in mentors" :key="mentor.id" :label="mentor.name" :value="mentor.id" />
          </el-select>
          <span class="spacer"></span>
          <el-button :disabled="!canAct" type="warning" plain @click="expireOffers">释放逾期意向</el-button>
        </div>

        <div class="table-wrap">
          <el-table :data="offers" row-key="id" stripe>
            <el-table-column label="学生" min-width="130">
              <template #default="{ row }">
                <strong>{{ row.student_name }}</strong>
                <div class="muted num">{{ row.student_no }}</div>
              </template>
            </el-table-column>
            <el-table-column label="导师 / 实训室" min-width="180">
              <template #default="{ row }">
                {{ row.mentor_name }}
                <div class="muted">{{ row.lab_name }}</div>
              </template>
            </el-table-column>
            <el-table-column label="类型" min-width="110">
              <template #default="{ row }"><StatusTag kind="offerType" :value="row.offer_type" /></template>
            </el-table-column>
            <el-table-column label="状态" min-width="100">
              <template #default="{ row }"><StatusTag kind="offerStatus" :value="row.status" /></template>
            </el-table-column>
            <el-table-column label="来源" min-width="150" prop="reason" show-overflow-tooltip />
            <el-table-column label="有效期至" min-width="155">
              <template #default="{ row }"><span class="num">{{ fmtDateTime(row.expires_at) }}</span></template>
            </el-table-column>
            <el-table-column label="确认时间" min-width="155">
              <template #default="{ row }"><span class="num">{{ fmtDateTime(row.confirmed_at) }}</span></template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-if="!offers.length && !loading" description="暂无拟录取记录" />
      </el-tab-pane>

      <el-tab-pane label="顺位补录" name="fill">
        <div class="pane-grid">
          <div class="card card--flat">
            <div class="card-title"><h3>释放名额并递补一名</h3></div>
            <el-form label-position="top">
              <el-form-item label="导师（显示剩余名额）">
                <el-select v-model="fillForm.mentor_id" filterable placeholder="选择导师" style="width: 100%">
                  <el-option
                    v-for="mentor in mentors"
                    :key="mentor.id"
                    :label="`${mentor.name} · ${mentor.lab_name} · 剩余 ${mentor.quota - mentor.quota_taken}`"
                    :value="mentor.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="轮次（可选）">
                <el-select v-model="fillForm.round_id" placeholder="默认最近一轮" clearable style="width: 100%">
                  <el-option v-for="round in rounds" :key="round.id" :label="round.name" :value="round.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="确认有效期（分钟）">
                <el-input-number v-model="fillForm.confirm_minutes" :min="1" :max="10080" style="width: 100%" />
              </el-form-item>
              <el-button type="primary" :disabled="!canAct" :loading="acting" @click="runFill">执行递补</el-button>
            </el-form>
          </div>
          <div class="card card--flat">
            <div class="card-title"><h3>递补结果</h3></div>
            <el-alert
              v-if="fillResult"
              :type="fillResult.filled ? 'success' : 'info'"
              :closable="false"
              :title="fillResult.filled ? '已生成递补拟录取记录' : '未产生递补'"
              :description="fillResult.filled ? `录取记录 #${fillResult.offer_id}，学生 ID ${fillResult.student_id}` : fillResult.reason"
            />
            <el-empty v-else description="还没有执行结果" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="统筹调剂" name="adjust">
        <div class="pane-grid">
          <div class="card card--flat">
            <div class="card-title"><h3>内部 → 跨室 → 约谈</h3></div>
            <el-form label-position="top">
              <el-form-item label="轮次">
                <el-select v-model="adjustForm.round_id" placeholder="选择轮次" style="width: 100%">
                  <el-option v-for="round in rounds" :key="round.id" :label="round.name" :value="round.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="确认有效期（分钟）">
                <el-input-number v-model="adjustForm.confirm_minutes" :min="1" :max="10080" style="width: 100%" />
              </el-form-item>
              <el-form-item label="预演模式">
                <div class="row">
                  <el-switch v-model="adjustForm.dry_run" />
                  <span class="muted">{{ adjustForm.dry_run ? '预演：仅计算、不落库' : '正式：会生成调剂记录' }}</span>
                </div>
              </el-form-item>
              <el-button type="primary" :disabled="!canAct" :loading="acting" @click="runAdjust">
                {{ adjustForm.dry_run ? '预演调剂' : '正式调剂' }}
              </el-button>
            </el-form>
          </div>
          <div class="card card--flat">
            <div class="card-title">
              <h3>调剂结果</h3>
              <span v-if="adjustResult" class="muted num">新建 {{ adjustResult.offers_created }} 条</span>
            </div>
            <template v-if="adjustResult">
              <h4 class="sub-title">分配名单</h4>
              <el-table :data="adjustResult.allocations" size="small">
                <el-table-column label="学生" min-width="120">
                  <template #default="{ row }">{{ studentName(row.student_id) }}</template>
                </el-table-column>
                <el-table-column label="导师" min-width="120">
                  <template #default="{ row }">{{ mentorName(row.mentor_id) }}</template>
                </el-table-column>
                <el-table-column label="优先级" width="100">
                  <template #default="{ row }">
                    <span class="pill" :class="row.mode === 'internal' ? 'pill--blue' : 'pill--green'">
                      {{ row.mode === 'internal' ? '内部' : '跨室' }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
              <h4 class="sub-title">待约谈名单</h4>
              <el-table :data="adjustResult.talk_list" size="small">
                <el-table-column label="学生" min-width="120">
                  <template #default="{ row }">{{ studentName(row.student_id) }}</template>
                </el-table-column>
                <el-table-column label="原实训室" min-width="120">
                  <template #default="{ row }">{{ labName(row.lab_id) }}</template>
                </el-table-column>
              </el-table>
              <el-empty v-if="!adjustResult.talk_list.length" description="没有需要约谈的学生" />
            </template>
            <el-empty v-else description="还没有执行结果" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="约谈安置" name="talk">
        <div class="pane-grid">
          <div class="card card--flat">
            <div class="card-title"><h3>最终统筹安置</h3></div>
            <el-form label-position="top">
              <el-form-item label="学生">
                <el-select v-model="talkForm.student_id" filterable placeholder="选择学生" style="width: 100%">
                  <el-option
                    v-for="student in students"
                    :key="student.id"
                    :label="`${student.name}（${student.student_no}）`"
                    :value="student.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="导师">
                <el-select v-model="talkForm.mentor_id" filterable placeholder="选择导师" style="width: 100%">
                  <el-option
                    v-for="mentor in mentors"
                    :key="mentor.id"
                    :label="`${mentor.name} · ${mentor.lab_name} · 剩余 ${mentor.quota - mentor.quota_taken}`"
                    :value="mentor.id"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="轮次">
                <el-select v-model="talkForm.round_id" placeholder="选择轮次" style="width: 100%">
                  <el-option v-for="round in rounds" :key="round.id" :label="round.name" :value="round.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="安置原因">
                <el-input v-model="talkForm.reason" maxlength="255" />
              </el-form-item>
              <el-button type="primary" :disabled="!canAct" :loading="acting" @click="runTalk">生成约谈安置</el-button>
            </el-form>
          </div>
          <div class="card card--flat">
            <div class="card-title"><h3>结果</h3></div>
            <el-alert
              v-if="talkResult"
              type="success"
              :closable="false"
              title="已生成约谈安置拟录取"
              :description="`记录 #${talkResult.offer_id} · 学生 ${studentName(talkResult.student_id)} · 导师 ${mentorName(talkResult.mentor_id)}`"
            />
            <el-empty v-else description="还没有执行结果" />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { OFFER_STATUS_TEXT, fmtDateTime } from '../../utils/format'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const canAct = computed(() => auth.isAdmin)

const loading = ref(true)
const acting = ref(false)
const rounds = ref([])
const mentors = ref([])
const students = ref([])
const offers = ref([])

const validTabs = ['run', 'offers', 'fill', 'adjust', 'talk']
const activeTab = ref(validTabs.includes(route.query.tab) ? String(route.query.tab) : 'run')

const runForm = reactive({ round_id: null, confirm_minutes: 120, dry_run: true })
const runResult = ref(null)
const offerRound = ref(null)
const offerStatus = ref('')
const offerMentor = ref(null)
const fillForm = reactive({ mentor_id: null, round_id: null, confirm_minutes: 120 })
const fillResult = ref(null)
const adjustForm = reactive({ round_id: null, confirm_minutes: 120, dry_run: true })
const adjustResult = ref(null)
const talkForm = reactive({ student_id: null, mentor_id: null, round_id: null, reason: '统筹安置' })
const talkResult = ref(null)

const studentMap = computed(() => new Map(students.value.map((student) => [student.id, student])))
const mentorMap = computed(() => new Map(mentors.value.map((mentor) => [mentor.id, mentor])))

function studentName(id) {
  const student = studentMap.value.get(id)
  return student ? `${student.name}（${student.student_no}）` : `学生 ${id}`
}

function mentorName(id) {
  return mentorMap.value.get(id)?.name || `导师 ${id}`
}

function labName(id) {
  const mentor = mentors.value.find((item) => item.lab_id === id)
  return mentor?.lab_name || `实训室 ${id}`
}

async function runSelection() {
  if (!canAct.value) return
  if (!runForm.round_id) {
    ElMessage.warning('请选择轮次')
    return
  }
  if (!runForm.dry_run) {
    await ElMessageBox.confirm(
      '正式执行会生成待确认拟录取记录并写入审计日志，是否继续？',
      '正式运行选拔',
      { confirmButtonText: '正式执行', cancelButtonText: '取消', type: 'warning' },
    )
  }
  acting.value = true
  try {
    runResult.value = await adminApi.runSelection({ ...runForm })
    ElMessage.success(runForm.dry_run ? '预演完成' : '选拔完成')
    await loadOffers()
  } finally {
    acting.value = false
  }
}

async function expireOffers() {
  if (!canAct.value) return
  await ElMessageBox.confirm('将释放所有已超过有效期的待确认记录，是否继续？', '释放逾期意向', {
    confirmButtonText: '释放',
    cancelButtonText: '取消',
    type: 'warning',
  })
  const result = await adminApi.expireOffers()
  ElMessage.success(`已释放 ${result.expired} 个逾期意向`)
  await loadOffers()
}

async function runFill() {
  if (!canAct.value) return
  if (!fillForm.mentor_id) {
    ElMessage.warning('请选择导师')
    return
  }
  acting.value = true
  try {
    fillResult.value = await adminApi.fillVacancy(fillForm.mentor_id, {
      round_id: fillForm.round_id || null,
      confirm_minutes: fillForm.confirm_minutes,
    })
    ElMessage.success(fillResult.value.filled ? '已生成递补记录' : '未产生递补')
    await loadOffers()
  } finally {
    acting.value = false
  }
}

async function runAdjust() {
  if (!canAct.value) return
  if (!adjustForm.round_id) {
    ElMessage.warning('请选择轮次')
    return
  }
  if (!adjustForm.dry_run) {
    await ElMessageBox.confirm('正式调剂会生成内部/跨室拟录取记录，是否继续？', '正式统筹调剂', {
      confirmButtonText: '正式执行',
      cancelButtonText: '取消',
      type: 'warning',
    })
  }
  acting.value = true
  try {
    adjustResult.value = await adminApi.adjust({ ...adjustForm })
    ElMessage.success(adjustForm.dry_run ? '调剂预演完成' : '调剂完成')
    await loadOffers()
  } finally {
    acting.value = false
  }
}

async function runTalk() {
  if (!canAct.value) return
  if (!talkForm.student_id || !talkForm.mentor_id || !talkForm.round_id) {
    ElMessage.warning('请选择学生、导师与轮次')
    return
  }
  acting.value = true
  try {
    talkResult.value = await adminApi.assignTalk({ ...talkForm })
    ElMessage.success('已生成约谈安置记录')
    await loadOffers()
  } finally {
    acting.value = false
  }
}

async function loadOffers() {
  const params = { limit: 500 }
  if (offerRound.value) params.round_id = offerRound.value
  if (offerStatus.value) params.status = offerStatus.value
  if (offerMentor.value) params.mentor_id = offerMentor.value
  const data = await adminApi.offers(params)
  offers.value = data.items || []
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
    const defaultRound =
      roundData.find((round) => round.is_open && round.kind === 'interview')?.id ||
      [...roundData].reverse().find((round) => round.kind === 'interview')?.id ||
      roundData.find((round) => round.is_open)?.id ||
      roundData[0]?.id ||
      null
    runForm.round_id = defaultRound
    adjustForm.round_id = defaultRound
    talkForm.round_id = defaultRound
    await loadOffers()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.tabs-card {
  padding: 8px 18px 18px;
}

.pane-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  gap: 16px;
  align-items: start;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.sub-title {
  margin: 16px 0 8px;
  font-size: 13px;
  color: var(--tls-ink-soft);
}

@media (max-width: 1000px) {
  .pane-grid {
    grid-template-columns: 1fr;
  }
}
</style>
