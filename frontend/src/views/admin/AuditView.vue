<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="审计日志"
      subtitle="记录改分、确认、逾期、补录、调剂、公示、申诉等关键动作的操作者、来源 IP 与前后值。"
      eyebrow="Admin / Audit"
    >
      <el-button @click="load">刷新</el-button>
    </PageHeader>

    <div class="card toolbar">
      <el-select v-model="action" placeholder="全部动作" clearable filterable style="width: 200px" @change="resetAndLoad">
        <el-option v-for="(label, key) in ACTION_TEXT" :key="key" :label="label" :value="key" />
      </el-select>
      <span class="spacer"></span>
      <span class="muted num">共 {{ total }} 条</span>
    </div>

    <div class="card">
      <div class="table-wrap">
        <el-table :data="logs" row-key="id" stripe>
          <el-table-column label="时间" width="160">
            <template #default="{ row }"><span class="num">{{ fmtDateTime(row.created_at) }}</span></template>
          </el-table-column>
          <el-table-column label="操作者" prop="actor" width="110" />
          <el-table-column label="动作" min-width="140">
            <template #default="{ row }">
              <span class="pill pill--blue">{{ actionText(row.action) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="对象" min-width="140">
            <template #default="{ row }">{{ row.entity }} #{{ row.entity_id }}</template>
          </el-table-column>
          <el-table-column label="IP" prop="ip" width="130" show-overflow-tooltip />
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-if="!logs.length && !loading" description="暂无审计记录" />
      <div class="pager">
        <el-pagination
          layout="prev, pager, next"
          :total="total"
          :page-size="limit"
          :current-page="page"
          @current-change="changePage"
        />
      </div>
    </div>

    <el-dialog v-model="detailVisible" title="审计详情" width="min(720px, 94vw)">
      <div class="detail-meta">
        <span class="pill pill--blue">{{ actionText(activeLog?.action) }}</span>
        <span class="muted">{{ activeLog?.entity }} #{{ activeLog?.entity_id }}</span>
        <span class="spacer"></span>
        <span class="muted num">{{ fmtDateTime(activeLog?.created_at) }}</span>
      </div>
      <div class="detail-grid">
        <div>
          <h4>变更前</h4>
          <pre>{{ jsonText(activeLog?.before_json) }}</pre>
        </div>
        <div>
          <h4>变更后</h4>
          <pre>{{ jsonText(activeLog?.after_json) }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import { ACTION_TEXT, actionText, fmtDateTime, jsonText } from '../../utils/format'

const loading = ref(true)
const logs = ref([])
const total = ref(0)
const action = ref('')
const limit = 100
const offset = ref(0)
const detailVisible = ref(false)
const activeLog = ref(null)

const page = computed(() => Math.floor(offset.value / limit) + 1)

function openDetail(row) {
  activeLog.value = row
  detailVisible.value = true
}

async function load() {
  const params = { limit, offset: offset.value }
  if (action.value) params.action = action.value
  const data = await adminApi.auditLogs(params)
  logs.value = data.items || []
  total.value = data.total || 0
}

function resetAndLoad() {
  offset.value = 0
  load()
}

function changePage(value) {
  offset.value = (value - 1) * limit
  load()
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
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 14px 16px;
  flex-wrap: wrap;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.detail-grid h4 {
  margin-bottom: 6px;
  font-size: 12.5px;
  color: var(--tls-ink-soft);
}

.detail-grid pre {
  margin: 0;
  max-height: 320px;
  overflow: auto;
  padding: 12px;
  border-radius: 10px;
  background: #f5f8fd;
  color: var(--tls-ink-soft);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 720px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
