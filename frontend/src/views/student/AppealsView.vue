<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="我的申诉"
      subtitle="公示期间可实名提出异议，管理员处理后会给出复核意见。申诉内容与回复全程留痕。"
      eyebrow="Appeals"
    />

    <div class="appeal-layout">
      <section class="card">
        <div class="card-title">
          <h3>新建实名申诉</h3>
        </div>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
          <el-form-item label="关联公示（可选）" prop="publication_id">
            <el-select v-model="form.publication_id" placeholder="选择要申诉的公示" clearable style="width: 100%">
              <el-option v-for="item in publications" :key="item.id" :label="item.title" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="申诉内容" prop="content">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="6"
              maxlength="2000"
              show-word-limit
              placeholder="请描述具体问题、涉及名单或轮次，并留下可核实的依据。"
            />
          </el-form-item>
          <el-button type="primary" :loading="submitting" @click="submit">提交申诉</el-button>
          <p class="muted tip">申诉为实名提交，处理结果会显示在右侧列表中。</p>
        </el-form>
      </section>

      <section class="stack">
        <div class="card">
          <div class="card-title">
            <h3>处理记录</h3>
            <span class="muted num">{{ appeals.length }} 条</span>
          </div>
          <div v-if="appeals.length" class="appeal-list">
            <article v-for="item in appeals" :key="item.id" class="appeal-item">
              <div class="row">
                <StatusTag kind="appeal" :value="item.status" />
                <span class="spacer"></span>
                <span class="muted num">{{ fmtDateTime(item.created_at) }}</span>
              </div>
              <p class="appeal-item__content">{{ item.content }}</p>
              <div v-if="item.reply" class="appeal-item__reply">
                <strong>复核意见</strong>
                <p>{{ item.reply }}</p>
                <span class="muted num">{{ fmtDateTime(item.handled_at) }}</span>
              </div>
              <div v-else class="muted appeal-item__pending">等待管理员处理</div>
            </article>
          </div>
          <el-empty v-else-if="!loading" description="还没有提交过申诉" />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { metaApi, studentApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { fmtDateTime } from '../../utils/format'

const loading = ref(true)
const submitting = ref(false)
const appeals = ref([])
const publications = ref([])
const formRef = ref(null)

const form = reactive({
  publication_id: null,
  content: '',
})

const rules = {
  content: [
    { required: true, message: '请填写申诉内容', trigger: 'blur' },
    { min: 5, max: 2000, message: '申诉内容需 5–2000 字', trigger: 'blur' },
  ],
}

async function loadAppeals() {
  appeals.value = await studentApi.appeals()
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await studentApi.createAppeal({
      publication_id: form.publication_id || null,
      content: form.content.trim(),
    })
    ElMessage.success('申诉已提交')
    form.content = ''
    await loadAppeals()
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const [appealData, publicationData] = await Promise.all([
      studentApi.appeals(),
      metaApi.publications(),
    ])
    appeals.value = appealData
    publications.value = publicationData
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.appeal-layout {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 18px;
  align-items: start;
}

.tip {
  margin-top: 10px;
  font-size: 11.5px;
}

.appeal-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.appeal-item {
  padding: 14px;
  border: 1px solid var(--tls-line);
  border-radius: 12px;
  background: #fbfdff;
}

.appeal-item__content {
  margin-top: 10px;
  color: var(--tls-ink-soft);
  font-size: 13px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.appeal-item__reply {
  margin-top: 12px;
  padding: 12px;
  border-radius: 10px;
  background: #f2f7fe;
}

.appeal-item__reply strong {
  font-size: 12px;
  color: var(--tls-primary-dark);
}

.appeal-item__reply p {
  margin-top: 4px;
  font-size: 12.5px;
  line-height: 1.8;
  color: var(--tls-ink-soft);
}

.appeal-item__reply span {
  display: block;
  margin-top: 6px;
  font-size: 11px;
}

.appeal-item__pending {
  margin-top: 10px;
  font-size: 12px;
}

@media (max-width: 900px) {
  .appeal-layout {
    grid-template-columns: 1fr;
  }
}
</style>
