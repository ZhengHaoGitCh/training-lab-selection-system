<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="管理仪表盘"
      subtitle="实训室、名额、志愿、面试与录取的实时汇总；关键动作都会写入审计日志。"
      eyebrow="Admin"
    >
      <el-button type="primary" @click="$router.push('/admin/selection')">运行选拔</el-button>
      <el-button @click="$router.push('/admin/publications')">发布公示</el-button>
    </PageHeader>

    <div class="stat-grid">
      <StatCard label="实训室" :value="dashboard.labs" suffix="个" tone="navy" />
      <StatCard label="导师" :value="dashboard.mentors" suffix="位" tone="blue" />
      <StatCard label="学生" :value="dashboard.students" suffix="人" tone="blue" />
      <StatCard label="总名额" :value="dashboard.quota_total" suffix="个" tone="green" :hint="`剩余 ${dashboard.quota_left ?? '—'} 个`" />
      <StatCard label="志愿记录" :value="dashboard.intentions" suffix="条" tone="navy" />
      <StatCard label="面试记录" :value="dashboard.interviews" suffix="条" tone="orange" />
      <StatCard label="待确认拟录取" :value="dashboard.offers_pending" suffix="个" tone="orange" hint="逾期将自动释放" />
      <StatCard label="已确认入组" :value="dashboard.offers_confirmed" suffix="人" tone="green" />
    </div>

    <section class="section grid grid-2">
      <div class="card">
        <div class="card-title">
          <h3>当前开放轮次</h3>
          <span class="muted">共 {{ dashboard.rounds_open?.length || 0 }} 个</span>
        </div>
        <div v-if="dashboard.rounds_open?.length" class="open-rounds">
          <div v-for="name in dashboard.rounds_open" :key="name" class="open-round">
            <span class="open-round__dot"></span>
            <strong>{{ name }}</strong>
            <span class="pill pill--green">进行中</span>
          </div>
        </div>
        <el-empty v-else description="当前没有开放轮次" />

        <div class="callout callout--orange" style="margin-top: 14px">
          正式运行选拔前建议先勾选“预演”，确认拟录取/递补人数无误后再正式执行。
        </div>
      </div>

      <div class="card">
        <div class="card-title">
          <h3>快捷操作</h3>
        </div>
        <div class="quick-grid">
          <router-link to="/admin/selection" class="quick-tile">
            <span>01</span>
            <strong>运行选拔</strong>
            <small>预演 / 正式生成拟录取</small>
          </router-link>
          <router-link to="/admin/selection?tab=offers" class="quick-tile">
            <span>02</span>
            <strong>逾期与补录</strong>
            <small>释放名额、顺位递补</small>
          </router-link>
          <router-link to="/admin/selection?tab=adjust" class="quick-tile">
            <span>03</span>
            <strong>统筹调剂</strong>
            <small>内部 → 跨室 → 约谈</small>
          </router-link>
          <router-link to="/admin/interviews" class="quick-tile">
            <span>04</span>
            <strong>面试评分</strong>
            <small>代录或校正四维分</small>
          </router-link>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="card">
        <div class="card-title">
          <h3>最近操作</h3>
          <router-link to="/admin/audit" class="link-more">查看全部审计 →</router-link>
        </div>
        <div class="table-wrap">
          <el-table :data="recentLogs" row-key="id" size="small">
            <el-table-column label="时间" width="160">
              <template #default="{ row }"><span class="num">{{ fmtDateTime(row.created_at) }}</span></template>
            </el-table-column>
            <el-table-column label="操作者" prop="actor" width="120" />
            <el-table-column label="动作" min-width="130">
              <template #default="{ row }">
                <span class="pill pill--blue">{{ actionText(row.action) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="对象" min-width="140">
              <template #default="{ row }">{{ row.entity }} #{{ row.entity_id }}</template>
            </el-table-column>
            <el-table-column label="IP" prop="ip" width="130" show-overflow-tooltip />
          </el-table>
        </div>
        <el-empty v-if="!recentLogs.length && !loading" description="暂无审计记录" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { adminApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import StatCard from '../../components/StatCard.vue'
import { actionText, fmtDateTime } from '../../utils/format'

const loading = ref(true)
const dashboard = ref({
  labs: 0,
  mentors: 0,
  quota_total: 0,
  students: 0,
  intentions: 0,
  interviews: 0,
  offers_pending: 0,
  offers_confirmed: 0,
  rounds_open: [],
  quota_left: 0,
})
const recentLogs = ref([])

onMounted(async () => {
  try {
    const [dashboardData, logData] = await Promise.all([
      adminApi.dashboard(),
      adminApi.auditLogs({ limit: 8 }),
    ])
    dashboard.value = dashboardData
    recentLogs.value = logData.items || []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.open-rounds {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.open-round {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f2f9f5;
  border: 1px solid #d8ece3;
}

.open-round__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--tls-green);
  box-shadow: 0 0 0 4px rgba(31, 122, 92, 0.14);
}

.open-round strong {
  flex: 1;
  font-size: 13.5px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.quick-tile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px;
  border: 1px solid var(--tls-line);
  border-radius: 12px;
  background: #f9fbff;
  transition: all 0.16s ease;
}

.quick-tile:hover {
  border-color: #b9d2ee;
  background: #f2f8ff;
  transform: translateY(-1px);
}

.quick-tile span {
  color: #b9c9de;
  font-size: 15px;
  font-weight: 800;
}

.quick-tile strong {
  color: var(--tls-ink);
  font-size: 13.5px;
}

.quick-tile small {
  color: var(--tls-muted);
  font-size: 11.5px;
}

.link-more {
  font-size: 12.5px;
  font-weight: 600;
}

@media (max-width: 560px) {
  .quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
