<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="轮次管理"
      subtitle="8 类轮次对应宣讲、开放日、填报、面试、确认、补录、调剂与公示；时间窗以服务端判定的开放状态为准。"
      eyebrow="Admin / Rounds"
    >
      <el-button v-if="canEdit" type="primary" @click="openDialog()">新建轮次</el-button>
    </PageHeader>

    <div class="card">
      <div class="table-wrap">
        <el-table :data="rounds" row-key="id" stripe>
          <el-table-column label="轮次" min-width="200">
            <template #default="{ row }">
              <strong>{{ row.name }}</strong>
              <div class="muted">第 {{ row.round_no }} 轮</div>
            </template>
          </el-table-column>
          <el-table-column label="类型" min-width="130">
            <template #default="{ row }"><StatusTag kind="roundKind" :value="row.kind" /></template>
          </el-table-column>
          <el-table-column label="开始" min-width="160">
            <template #default="{ row }"><span class="num">{{ fmtDateTime(row.starts_at) }}</span></template>
          </el-table-column>
          <el-table-column label="结束" min-width="160">
            <template #default="{ row }"><span class="num">{{ fmtDateTime(row.ends_at) }}</span></template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <span class="pill" :class="row.is_open ? 'pill--green' : 'pill--muted'">
                {{ row.is_open ? '进行中' : '未开放' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column v-if="canEdit" label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-if="!rounds.length && !loading" description="暂无轮次" />
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑轮次' : '新建轮次'" width="min(560px, 94vw)">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="64" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="类型" prop="kind">
            <el-select v-model="form.kind" style="width: 100%">
              <el-option
                v-for="(label, kind) in ROUND_KIND_TEXT"
                :key="kind"
                :label="label"
                :value="kind"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="轮次序号" prop="round_no">
            <el-input-number v-model="form.round_no" :min="1" :max="10" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="开始时间" prop="starts_at">
            <el-date-picker
              v-model="form.starts_at"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="结束时间" prop="ends_at">
            <el-date-picker
              v-model="form.ends_at"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm"
              style="width: 100%"
            />
          </el-form-item>
        </div>
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
import { ROUND_KIND_TEXT, fmtDateTime, fromLocalInput, toLocalInput } from '../../utils/format'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const canEdit = computed(() => auth.isAdmin)

const loading = ref(true)
const saving = ref(false)
const rounds = ref([])
const dialogVisible = ref(false)
const editing = ref(null)
const formRef = ref(null)

const form = reactive({
  name: '',
  kind: 'intention',
  round_no: 1,
  starts_at: '',
  ends_at: '',
})

const rules = {
  name: [{ required: true, message: '请输入轮次名称', trigger: 'blur' }],
  kind: [{ required: true, message: '请选择类型', trigger: 'change' }],
  round_no: [{ required: true, message: '请输入轮次序号', trigger: 'change' }],
  starts_at: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  ends_at: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
}

function openDialog(round = null) {
  editing.value = round
  Object.assign(form, {
    name: round?.name || '',
    kind: round?.kind || 'intention',
    round_no: round?.round_no ?? 1,
    starts_at: round ? toLocalInput(round.starts_at) : '',
    ends_at: round ? toLocalInput(round.ends_at) : '',
  })
  dialogVisible.value = true
}

async function save() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const payload = {
    name: form.name.trim(),
    kind: form.kind,
    round_no: form.round_no,
    starts_at: fromLocalInput(form.starts_at),
    ends_at: fromLocalInput(form.ends_at),
  }
  if (payload.starts_at >= payload.ends_at) {
    ElMessage.warning('结束时间必须晚于开始时间')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await adminApi.updateRound(editing.value.id, payload)
      ElMessage.success('轮次已更新')
    } else {
      await adminApi.createRound(payload)
      ElMessage.success('轮次已创建')
    }
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function load() {
  rounds.value = await adminApi.rounds()
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
