<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="实训室与导师"
      subtitle="维护实训室容量、项目方向与开放日；导师名额合计不能超过所属实训室容量。"
      eyebrow="Admin / Labs"
    >
      <el-button v-if="canEdit" type="primary" @click="openLabDialog()">新建实训室</el-button>
    </PageHeader>

    <div v-if="!canEdit" class="callout" style="margin-bottom: 14px">
      当前角色为只读（监督），不能新增、修改或删除基础数据。
    </div>

    <el-tabs v-model="tab" class="card tabs-card">
      <el-tab-pane label="实训室" name="labs">
        <div class="table-wrap">
          <el-table :data="labs" row-key="id" stripe>
            <el-table-column label="实训室" min-width="200">
              <template #default="{ row }">
                <strong>{{ row.name }}</strong>
                <div class="muted">{{ row.direction || '综合方向' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="容量" prop="capacity" width="90" />
            <el-table-column label="导师" prop="mentor_count" width="90" />
            <el-table-column label="名额合计" prop="quota_total" width="110" />
            <el-table-column label="名额使用" min-width="170">
              <template #default="{ row }">
                <el-progress
                  :percentage="quotaPercent(row.quota_total, row.capacity)"
                  :stroke-width="8"
                  :show-text="false"
                  :color="row.quota_total > row.capacity ? '#e8772e' : '#2f6fba'"
                />
                <span class="muted num">{{ row.quota_total }} / {{ row.capacity }}</span>
              </template>
            </el-table-column>
            <el-table-column label="开放日" min-width="160">
              <template #default="{ row }"><span class="num">{{ fmtDateTime(row.open_day_at) }}</span></template>
            </el-table-column>
            <el-table-column v-if="canEdit" label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openLabDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeLab(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-if="!labs.length && !loading" description="暂无实训室" />
      </el-tab-pane>

      <el-tab-pane label="导师" name="mentors">
        <div class="toolbar">
          <el-select v-model="mentorLabFilter" placeholder="全部实训室" clearable style="width: 220px">
            <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
          </el-select>
          <span class="spacer"></span>
          <el-button v-if="canEdit" type="primary" @click="openMentorDialog()">新建导师</el-button>
        </div>
        <div class="table-wrap">
          <el-table :data="filteredMentors" row-key="id" stripe>
            <el-table-column label="导师" min-width="140">
              <template #default="{ row }">
                <strong>{{ row.name }}</strong>
                <div class="muted">ID {{ row.id }}</div>
              </template>
            </el-table-column>
            <el-table-column label="所属实训室" min-width="170" prop="lab_name" />
            <el-table-column label="名额" min-width="150">
              <template #default="{ row }">
                <span class="num">{{ row.quota - row.quota_taken }} / {{ row.quota }}</span>
                <div class="muted">已占用 {{ row.quota_taken }}</div>
              </template>
            </el-table-column>
            <el-table-column label="考核要求" min-width="220" prop="requirement" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-switch
                  :model-value="row.is_active"
                  :disabled="!canEdit"
                  @change="(value) => setMentorActive(row, value)"
                />
              </template>
            </el-table-column>
            <el-table-column v-if="canEdit" label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openMentorDialog(row)">编辑</el-button>
                <el-button link type="danger" @click="removeMentor(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-if="!filteredMentors.length && !loading" description="暂无导师" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="labDialogVisible" :title="editingLab ? '编辑实训室' : '新建实训室'" width="min(560px, 94vw)">
      <el-form ref="labFormRef" :model="labForm" :rules="labRules" label-position="top">
        <el-form-item label="名称" prop="name">
          <el-input v-model="labForm.name" maxlength="64" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="容量" prop="capacity">
            <el-input-number v-model="labForm.capacity" :min="0" :max="1000" style="width: 100%" />
          </el-form-item>
          <el-form-item label="项目方向">
            <el-input v-model="labForm.direction" maxlength="128" />
          </el-form-item>
        </div>
        <el-form-item label="简介">
          <el-input v-model="labForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="开放日">
          <el-date-picker
            v-model="labForm.open_day_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm"
            placeholder="可选"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="labDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveLab">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="mentorDialogVisible" :title="editingMentor ? '编辑导师' : '新建导师'" width="min(560px, 94vw)">
      <el-form ref="mentorFormRef" :model="mentorForm" :rules="mentorRules" label-position="top">
        <el-form-item label="所属实训室" prop="lab_id">
          <el-select v-model="mentorForm.lab_id" style="width: 100%">
            <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
          </el-select>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="导师姓名" prop="name">
            <el-input v-model="mentorForm.name" maxlength="64" />
          </el-form-item>
          <el-form-item label="招录名额" prop="quota">
            <el-input-number v-model="mentorForm.quota" :min="0" :max="1000" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="考核要求">
          <el-input v-model="mentorForm.requirement" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mentorDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveMentor">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import { fmtDateTime, fromLocalInput, quotaPercent, toLocalInput } from '../../utils/format'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const canEdit = computed(() => auth.isAdmin)

const loading = ref(true)
const saving = ref(false)
const tab = ref('labs')
const labs = ref([])
const mentors = ref([])
const mentorLabFilter = ref(null)

const labDialogVisible = ref(false)
const editingLab = ref(null)
const labFormRef = ref(null)
const labForm = reactive({
  name: '',
  capacity: 10,
  direction: '',
  description: '',
  open_day_at: '',
})

const mentorDialogVisible = ref(false)
const editingMentor = ref(null)
const mentorFormRef = ref(null)
const mentorForm = reactive({
  lab_id: null,
  name: '',
  quota: 4,
  requirement: '',
})

const labRules = {
  name: [{ required: true, message: '请输入实训室名称', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容量', trigger: 'change' }],
}

const mentorRules = {
  lab_id: [{ required: true, message: '请选择实训室', trigger: 'change' }],
  name: [{ required: true, message: '请输入导师姓名', trigger: 'blur' }],
  quota: [{ required: true, message: '请输入名额', trigger: 'change' }],
}

const filteredMentors = computed(() => {
  if (!mentorLabFilter.value) return mentors.value
  return mentors.value.filter((mentor) => mentor.lab_id === mentorLabFilter.value)
})

function openLabDialog(lab = null) {
  editingLab.value = lab
  Object.assign(labForm, {
    name: lab?.name || '',
    capacity: lab?.capacity ?? 10,
    direction: lab?.direction || '',
    description: lab?.description || '',
    open_day_at: lab?.open_day_at ? toLocalInput(lab.open_day_at) : '',
  })
  labDialogVisible.value = true
}

async function saveLab() {
  const valid = await labFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      name: labForm.name.trim(),
      capacity: labForm.capacity,
      direction: labForm.direction,
      description: labForm.description,
      open_day_at: fromLocalInput(labForm.open_day_at),
    }
    if (editingLab.value) {
      await adminApi.updateLab(editingLab.value.id, payload)
      ElMessage.success('实训室已更新')
    } else {
      await adminApi.createLab(payload)
      ElMessage.success('实训室已创建')
    }
    labDialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function removeLab(lab) {
  await ElMessageBox.confirm(
    `删除「${lab.name}」？若已有志愿记录，后端会拒绝删除。`,
    '删除实训室',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
  )
  await adminApi.deleteLab(lab.id)
  ElMessage.success('已删除')
  await load()
}

function openMentorDialog(mentor = null) {
  editingMentor.value = mentor
  Object.assign(mentorForm, {
    lab_id: mentor?.lab_id ?? labs.value[0]?.id ?? null,
    name: mentor?.name || '',
    quota: mentor?.quota ?? 4,
    requirement: mentor?.requirement || '',
  })
  mentorDialogVisible.value = true
}

async function saveMentor() {
  const valid = await mentorFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = {
      lab_id: mentorForm.lab_id,
      name: mentorForm.name.trim(),
      quota: mentorForm.quota,
      requirement: mentorForm.requirement,
    }
    if (editingMentor.value) {
      await adminApi.updateMentor(editingMentor.value.id, payload)
      ElMessage.success('导师已更新')
    } else {
      await adminApi.createMentor(payload)
      ElMessage.success('导师已创建')
    }
    mentorDialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function setMentorActive(mentor, value) {
  try {
    await adminApi.updateMentor(mentor.id, { is_active: value })
    mentor.is_active = value
    ElMessage.success(value ? '导师已启用' : '导师已停用')
  } catch {
    mentor.is_active = !value
  }
}

async function removeMentor(mentor) {
  await ElMessageBox.confirm(
    `删除导师「${mentor.name}」？已有志愿记录时建议改为停用。`,
    '删除导师',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
  )
  await adminApi.deleteMentor(mentor.id)
  ElMessage.success('已删除')
  await load()
}

async function load() {
  const [labData, mentorData] = await Promise.all([adminApi.labs(), adminApi.mentors()])
  labs.value = labData
  mentors.value = mentorData
}

onMounted(async () => {
  try {
    await load()
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

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 14px;
}

@media (max-width: 620px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
