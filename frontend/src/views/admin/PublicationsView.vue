<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="公示与申诉"
      subtitle="发布录取/补录/调剂公示，处理实名异议，并查看最终入组名单。公示默认对外可见。"
      eyebrow="Admin / Publications"
    >
      <el-button type="primary" @click="openCreate">新建公示</el-button>
    </PageHeader>

    <el-tabs v-model="tab" class="card tabs-card" @tab-change="onTabChange">
      <el-tab-pane label="公示管理" name="publications">
        <div class="table-wrap">
          <el-table :data="publications" row-key="id" stripe>
            <el-table-column label="标题" min-width="220">
              <template #default="{ row }">
                <strong>{{ row.title }}</strong>
                <div class="muted">{{ row.content ? row.content.slice(0, 48) : '暂无正文' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="关联轮次" min-width="130">
              <template #default="{ row }">{{ row.round_id ? roundName(row.round_id) : '—' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }"><StatusTag kind="publication" :value="row.status" /></template>
            </el-table-column>
            <el-table-column label="创建时间" min-width="155">
              <template #default="{ row }"><span class="num">{{ fmtDateTime(row.created_at) }}</span></template>
            </el-table-column>
            <el-table-column label="发布时间" min-width="155">
              <template #default="{ row }"><span class="num">{{ fmtDateTime(row.published_at) }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="viewPublication(row)">查看</el-button>
                <el-button v-if="row.status === 'draft'" link type="success" @click="publish(row)">发布</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-if="!publications.length && !loading" description="暂无公示" />
      </el-tab-pane>

      <el-tab-pane label="申诉处理" name="appeals">
        <div class="toolbar">
          <el-select v-model="appealStatus" placeholder="全部状态" clearable style="width: 160px" @change="loadAppeals">
            <el-option v-for="(label, status) in APPEAL_STATUS_TEXT" :key="status" :label="label" :value="status" />
          </el-select>
          <span class="spacer"></span>
          <span class="muted">实名申诉，处理结果会反馈给学生</span>
        </div>
        <div class="table-wrap">
          <el-table :data="appeals" row-key="id" stripe>
            <el-table-column label="学生" min-width="120">
              <template #default="{ row }"><strong>{{ row.student_name }}</strong></template>
            </el-table-column>
            <el-table-column label="关联公示" min-width="140">
              <template #default="{ row }">{{ row.publication_id ? `#${row.publication_id}` : '未关联' }}</template>
            </el-table-column>
            <el-table-column label="申诉内容" min-width="260">
              <template #default="{ row }">
                <span class="appeal-content">{{ row.content }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }"><StatusTag kind="appeal" :value="row.status" /></template>
            </el-table-column>
            <el-table-column label="提交时间" min-width="155">
              <template #default="{ row }"><span class="num">{{ fmtDateTime(row.created_at) }}</span></template>
            </el-table-column>
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openHandle(row)">处理</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-if="!appeals.length && !loading" description="暂无申诉" />
      </el-tab-pane>

      <el-tab-pane label="入组名单" name="enrollment">
        <div class="table-wrap">
          <el-table :data="enrollment" row-key="student_no" stripe>
            <el-table-column label="学号" prop="student_no" min-width="120" />
            <el-table-column label="姓名" prop="student_name" min-width="110" />
            <el-table-column label="导师" prop="mentor_name" min-width="120" />
            <el-table-column label="实训室" prop="lab_name" min-width="180" />
            <el-table-column label="确认时间" min-width="160">
              <template #default="{ row }"><span class="num">{{ fmtDateTime(row.confirmed_at) }}</span></template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-if="!enrollment.length && !loading" description="暂无已确认入组学生" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="createVisible" title="新建公示" width="min(620px, 94vw)">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-position="top">
        <el-form-item label="标题" prop="title">
          <el-input v-model="createForm.title" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="关联轮次（可选）">
          <el-select v-model="createForm.round_id" clearable placeholder="不关联轮次" style="width: 100%">
            <el-option v-for="round in rounds" :key="round.id" :label="round.name" :value="round.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="createForm.content" type="textarea" :rows="8" placeholder="支持换行，发布后对外可见" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createPublication">保存草稿</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="viewVisible" :title="activePublication?.title" width="min(680px, 94vw)">
      <p class="muted num">发布于 {{ fmtDateTime(activePublication?.published_at) }}</p>
      <div class="publication-body">{{ activePublication?.content || '暂无正文' }}</div>
    </el-dialog>

    <el-dialog v-model="handleVisible" :title="`处理申诉 · ${activeAppeal?.student_name || ''}`" width="min(620px, 94vw)">
      <div class="appeal-quote">{{ activeAppeal?.content }}</div>
      <el-form ref="handleFormRef" :model="handleForm" :rules="handleRules" label-position="top">
        <el-form-item label="处理结果" prop="status">
          <el-select v-model="handleForm.status" style="width: 100%">
            <el-option label="已受理" value="accepted" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="已办结" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核意见" prop="reply">
          <el-input v-model="handleForm.reply" type="textarea" :rows="5" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleAppeal">提交处理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { APPEAL_STATUS_TEXT, fmtDateTime } from '../../utils/format'

const loading = ref(true)
const saving = ref(false)
const tab = ref('publications')
const publications = ref([])
const appeals = ref([])
const enrollment = ref([])
const rounds = ref([])
const appealStatus = ref('')

const createVisible = ref(false)
const createFormRef = ref(null)
const createForm = reactive({ title: '', round_id: null, content: '' })
const createRules = {
  title: [{ required: true, message: '请输入公示标题', trigger: 'blur' }],
}

const viewVisible = ref(false)
const activePublication = ref(null)

const handleVisible = ref(false)
const handleFormRef = ref(null)
const activeAppeal = ref(null)
const handleForm = reactive({ status: 'accepted', reply: '' })
const handleRules = {
  reply: [{ required: true, message: '请输入复核意见', trigger: 'blur' }],
}

function roundName(id) {
  return rounds.value.find((round) => round.id === id)?.name || `轮次 ${id}`
}

function openCreate() {
  Object.assign(createForm, { title: '', round_id: null, content: '' })
  createVisible.value = true
}

async function createPublication() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await adminApi.createPublication({
      title: createForm.title.trim(),
      round_id: createForm.round_id || null,
      content: createForm.content,
    })
    ElMessage.success('公示草稿已创建')
    createVisible.value = false
    await loadPublications()
  } finally {
    saving.value = false
  }
}

function viewPublication(row) {
  activePublication.value = row
  viewVisible.value = true
}

async function publish(row) {
  await ElMessageBox.confirm(`发布公示「${row.title}」？发布后对学生与访客可见。`, '发布公示', {
    confirmButtonText: '发布',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await adminApi.publishPublication(row.id)
  ElMessage.success('公示已发布')
  await loadPublications()
}

function openHandle(row) {
  activeAppeal.value = row
  handleForm.status = row.status === 'open' ? 'accepted' : row.status
  handleForm.reply = row.reply || ''
  handleVisible.value = true
}

async function handleAppeal() {
  const valid = await handleFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await adminApi.handleAppeal(activeAppeal.value.id, { ...handleForm })
    ElMessage.success('申诉已处理')
    handleVisible.value = false
    await loadAppeals()
  } finally {
    saving.value = false
  }
}

async function loadPublications() {
  publications.value = await adminApi.publications()
}

async function loadAppeals() {
  const params = appealStatus.value ? { status: appealStatus.value } : {}
  appeals.value = await adminApi.appeals(params)
}

function onTabChange(name) {
  if (name === 'appeals') loadAppeals()
  if (name === 'enrollment') loadEnrollment()
}

async function loadEnrollment() {
  enrollment.value = await adminApi.enrollment()
}

onMounted(async () => {
  try {
    const [publicationData, roundData, enrollmentData, appealData] = await Promise.all([
      adminApi.publications(),
      adminApi.rounds(),
      adminApi.enrollment(),
      adminApi.appeals(),
    ])
    publications.value = publicationData
    rounds.value = roundData
    enrollment.value = enrollmentData
    appeals.value = appealData
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.tabs-card {
  padding: 8px 18px 18px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.appeal-content {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.publication-body,
.appeal-quote {
  margin-top: 12px;
  color: var(--tls-ink-soft);
  line-height: 1.9;
  white-space: pre-wrap;
}

.appeal-quote {
  margin-top: 0;
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f6f9fd;
  color: var(--tls-muted);
  font-size: 13px;
}
</style>
