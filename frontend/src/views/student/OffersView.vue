<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="拟录取"
      subtitle="仅收到 1 个拟录取意向时自动确认；收到 2 个及以上时，必须在窗口内选择唯一去向，逾期视为放弃。"
      eyebrow="Offers"
    >
      <span v-if="pendingOffers.length" class="pill pill--orange">{{ pendingOffers.length }} 个待确认</span>
      <span v-else class="pill pill--muted">暂无待确认</span>
    </PageHeader>

    <div v-if="confirmedOffer" class="callout callout--success">
      你已确认入组：<strong>{{ confirmedOffer.lab_name }}</strong> · {{ confirmedOffer.mentor_name }}。
      确认时间：{{ fmtDateTime(confirmedOffer.confirmed_at) }}。如需变更请联系学院。
    </div>

    <div v-if="pendingOffers.length" class="card pending-card">
      <div class="pending-card__text">
        <h3>待确认的拟录取</h3>
        <p class="muted">
          你有 {{ pendingOffers.length }} 个待确认意向。
          {{ pendingOffers.length > 1 ? '请选择唯一去向，其余意向将被释放。' : '确认后即完成入组。' }}
        </p>
      </div>
      <el-button type="primary" size="large" @click="openConfirm">确认唯一去向</el-button>
    </div>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>全部录取记录</h2>
          <p>包含拟录取、递补、内部调剂、跨室调剂与约谈安置记录。</p>
        </div>
      </div>

      <div v-if="offers.length" class="stack">
        <article v-for="offer in offers" :key="offer.id" class="card offer-card">
          <div class="offer-card__head">
            <div class="row">
              <StatusTag kind="offerType" :value="offer.offer_type" />
              <StatusTag kind="offerStatus" :value="offer.status" />
              <span v-if="isExpired(offer) && offer.status === 'pending'" class="pill pill--orange">已超出有效期</span>
            </div>
            <span class="muted num">#{{ offer.id }}</span>
          </div>

          <div class="offer-card__body">
            <div>
              <h3>{{ offer.mentor_name }}</h3>
              <p class="muted">{{ offer.lab_name }}</p>
            </div>
            <div class="offer-card__meta">
              <div><span class="muted">来源</span><strong>{{ offer.reason || '—' }}</strong></div>
              <div><span class="muted">创建</span><strong class="num">{{ fmtDateTime(offer.created_at) }}</strong></div>
              <div><span class="muted">有效期至</span><strong class="num">{{ fmtDateTime(offer.expires_at) }}</strong></div>
              <div v-if="offer.confirmed_at"><span class="muted">确认时间</span><strong class="num">{{ fmtDateTime(offer.confirmed_at) }}</strong></div>
            </div>
          </div>
        </article>
      </div>
      <el-empty v-else-if="!loading" description="暂无录取记录，请等待管理员运行选拔" />
    </section>

    <el-dialog v-model="confirmVisible" title="确认唯一去向" width="min(560px, 92vw)">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="确认后不可更改"
        description="确认一个去向，其余待确认意向将自动释放；逾期未确认视为放弃并进入递补。"
      />
      <el-radio-group v-model="chosenMentorId" class="offer-choices">
        <el-radio v-for="offer in pendingOffers" :key="offer.id" :value="offer.mentor_id" border>
          <div class="offer-choice">
            <strong>{{ offer.mentor_name }}</strong>
            <span class="muted">{{ offer.lab_name }} · {{ OFFER_TYPE_TEXT[offer.offer_type] || offer.offer_type }}</span>
            <span class="muted num">有效期至 {{ fmtDateTime(offer.expires_at) }}</span>
          </div>
        </el-radio>
      </el-radio-group>
      <template #footer>
        <el-button @click="confirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="confirming" @click="confirm">确认去向</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { studentApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import {
  OFFER_TYPE_TEXT,
  fmtDateTime,
  parseServerTime,
} from '../../utils/format'

const loading = ref(true)
const confirming = ref(false)
const offers = ref([])
const confirmVisible = ref(false)
const chosenMentorId = ref(null)

const pendingOffers = computed(() => offers.value.filter((offer) => offer.status === 'pending'))
const confirmedOffer = computed(() => offers.value.find((offer) => offer.status === 'confirmed') || null)

function isExpired(offer) {
  if (!offer?.expires_at) return false
  return (parseServerTime(offer.expires_at)?.getTime() ?? 0) < Date.now()
}

function openConfirm() {
  if (!pendingOffers.value.length) return
  chosenMentorId.value = pendingOffers.value.length === 1 ? pendingOffers.value[0].mentor_id : null
  confirmVisible.value = true
}

async function confirm() {
  const offer = pendingOffers.value.find((item) => item.mentor_id === chosenMentorId.value)
  if (!offer) {
    ElMessage.warning('请选择一个去向')
    return
  }
  confirming.value = true
  try {
    await studentApi.confirmOffer({ mentor_id: offer.mentor_id })
    ElMessage.success('确认成功，你已入组')
    confirmVisible.value = false
    await load()
  } finally {
    confirming.value = false
  }
}

async function load() {
  offers.value = await studentApi.offers()
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
.callout--success {
  border-color: var(--tls-green);
  background: var(--tls-green-soft);
  color: #175f48;
}

.pending-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
  border-color: #f3c8a9;
  background: linear-gradient(180deg, #fff 0%, #fff8f2 100%);
}

.pending-card h3 {
  font-size: 17px;
}

.pending-card p {
  margin-top: 6px;
  font-size: 12.5px;
  line-height: 1.7;
}

.offer-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.offer-card__body {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-top: 12px;
}

.offer-card__body h3 {
  font-size: 17px;
}

.offer-card__body p {
  margin-top: 4px;
  font-size: 12.5px;
}

.offer-card__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(150px, 1fr));
  gap: 8px 24px;
  min-width: min(420px, 100%);
}

.offer-card__meta div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.offer-card__meta span {
  font-size: 11px;
}

.offer-card__meta strong {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tls-ink-soft);
}

.offer-choices {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
  width: 100%;
}

.offer-choices :deep(.el-radio) {
  width: 100%;
  height: auto;
  margin: 0;
  padding: 12px 14px;
}

.offer-choice {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.offer-choice strong {
  font-size: 14px;
}

.offer-choice span {
  font-size: 12px;
}

@media (max-width: 768px) {
  .pending-card,
  .offer-card__body {
    align-items: flex-start;
    flex-direction: column;
  }

  .offer-card__meta {
    grid-template-columns: 1fr;
    width: 100%;
  }
}
</style>
