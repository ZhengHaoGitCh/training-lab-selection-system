<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="我的名单"
      subtitle="展示你名下的拟录取、递补、内部/跨室调剂与约谈安置记录；学生确认后状态变为“已确认”。"
      eyebrow="Offers"
    >
      <span class="pill pill--blue">剩余名额 {{ profile?.quota_left ?? '—' }}</span>
    </PageHeader>

    <div class="stat-grid">
      <StatCard label="名额总数" :value="profile?.mentor.quota ?? 0" suffix="个" tone="navy" />
      <StatCard label="已占用" :value="profile?.quota_taken ?? 0" suffix="个" tone="orange" hint="含待确认与已确认" />
      <StatCard label="待确认" :value="pendingCount" suffix="个" tone="green" />
      <StatCard label="已确认" :value="confirmedCount" suffix="人" tone="blue" />
    </div>

    <div class="card toolbar">
      <el-select v-model="status" placeholder="全部状态" style="width: 180px" @change="load">
        <el-option label="全部状态" value="" />
        <el-option label="待确认" value="pending" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="已放弃" value="rejected" />
        <el-option label="已过期" value="expired" />
      </el-select>
      <span class="spacer"></span>
      <span class="muted">按创建时间倒序</span>
    </div>

    <div class="card">
      <div class="table-wrap">
        <el-table :data="offers" row-key="id" stripe>
          <el-table-column label="学生" min-width="150">
            <template #default="{ row }">
              <div class="student-cell">
                <span class="student-cell__avatar">{{ (row.student_name || '?').slice(0, 1) }}</span>
                <div>
                  <strong>{{ row.student_name || `学生 ${row.student_id}` }}</strong>
                  <small class="num">{{ row.student_no }}</small>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="类型" min-width="110">
            <template #default="{ row }"><StatusTag kind="offerType" :value="row.offer_type" /></template>
          </el-table-column>
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }"><StatusTag kind="offerStatus" :value="row.status" /></template>
          </el-table-column>
          <el-table-column label="来源" min-width="150" prop="reason" show-overflow-tooltip />
          <el-table-column label="有效期至" min-width="160">
            <template #default="{ row }"><span class="num">{{ fmtDateTime(row.expires_at) }}</span></template>
          </el-table-column>
          <el-table-column label="确认时间" min-width="160">
            <template #default="{ row }"><span class="num">{{ fmtDateTime(row.confirmed_at) }}</span></template>
          </el-table-column>
        </el-table>
      </div>
      <el-empty v-if="!offers.length && !loading" description="暂无录取记录" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { teacherApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import StatCard from '../../components/StatCard.vue'
import StatusTag from '../../components/StatusTag.vue'
import { fmtDateTime } from '../../utils/format'

const loading = ref(true)
const offers = ref([])
const profile = ref(null)
const status = ref('')

const pendingCount = computed(() => offers.value.filter((row) => row.status === 'pending').length)
const confirmedCount = computed(() => offers.value.filter((row) => row.status === 'confirmed').length)

async function load() {
  const params = status.value ? { status: status.value } : {}
  offers.value = await teacherApi.offers(params)
}

onMounted(async () => {
  try {
    const [profileData] = await Promise.all([teacherApi.profile(), load()])
    profile.value = profileData
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
</style>
