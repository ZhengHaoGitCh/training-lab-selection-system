<template>
  <div class="page" v-loading="loading">
    <PageHeader
      title="志愿填报"
      subtitle="最多选择 3 个平行导师意向，不分志愿先后；同时设置是否服从实训室内部调剂与全院跨实训室调剂。"
      eyebrow="Intentions"
    >
      <span class="pill pill--blue">已选 {{ selected.length }} / 3</span>
    </PageHeader>

    <div class="card round-bar">
      <div class="round-bar__left">
        <span class="muted">填报轮次</span>
        <el-select v-model="roundId" placeholder="选择填报轮次" style="width: min(420px, 100%)">
          <el-option
            v-for="round in intentionRounds"
            :key="round.id"
            :label="`${round.name}（${fmtDateTime(round.starts_at)} ~ ${fmtDateTime(round.ends_at)}）`"
            :value="round.id"
          />
        </el-select>
      </div>
      <div class="row">
        <span v-if="selectedRound" class="pill" :class="roundState(selectedRound).key === 'open' ? 'pill--green' : 'pill--orange'">
          {{ roundState(selectedRound).text }}
        </span>
        <span v-if="selectedRound" class="muted num round-bar__time">
          {{ fmtDateTime(selectedRound.starts_at) }} ~ {{ fmtDateTime(selectedRound.ends_at) }}
        </span>
      </div>
    </div>

    <el-empty v-if="!intentionRounds.length && !loading" description="暂无志愿填报轮次，请等待学院通知" />

    <div v-else class="intention-layout">
      <section class="stack">
        <div v-for="lab in labs" :key="lab.id" class="card">
          <div class="lab-head">
            <div>
              <div class="row">
                <h3>{{ lab.name }}</h3>
                <span class="pill pill--blue">{{ lab.direction || '综合方向' }}</span>
              </div>
              <p class="muted">{{ lab.description || '项目方向与培养安排以宣讲会为准。' }}</p>
            </div>
            <span class="muted num">容量 {{ lab.capacity }}</span>
          </div>

          <div class="mentor-grid">
            <article
              v-for="mentor in lab.mentors"
              :key="mentor.id"
              class="mentor-card"
              :class="{
                'is-selected': isSelected(mentor.id),
                'is-disabled': !isSelected(mentor.id) && selected.length >= 3,
              }"
              @click="toggleMentor(mentor)"
            >
              <div class="mentor-card__top">
                <el-checkbox :model-value="isSelected(mentor.id)" class="mentor-card__check" />
                <div class="mentor-card__name">
                  <strong>{{ mentor.name }}</strong>
                  <span class="muted">导师志愿</span>
                </div>
                <span class="mentor-card__quota num">
                  {{ mentor.quota_left }}<small>/{{ mentor.quota }}</small>
                </span>
              </div>
              <p class="mentor-card__req">{{ mentor.requirement || '考核要求以导师说明为准。' }}</p>
              <div class="mentor-card__foot">
                <span class="pill" :class="mentor.quota_left > 0 ? 'pill--green' : 'pill--muted'">
                  {{ mentor.quota_left > 0 ? `剩余 ${mentor.quota_left} 个名额` : '名额已满' }}
                </span>
                <span v-if="isSelected(mentor.id)" class="pill pill--blue">已加入志愿</span>
              </div>
            </article>
          </div>
        </div>
        <el-empty v-if="!labs.length && !loading" description="暂无实训室与导师数据" />
      </section>

      <aside class="stack">
        <div class="card">
          <div class="card-title">
            <h3>平行志愿</h3>
            <span class="muted num">{{ selected.length }}/3</span>
          </div>
          <div v-if="selectedMentors.length" class="selected-list">
            <div v-for="mentor in selectedMentors" :key="mentor.id" class="selected-item">
              <div>
                <strong>{{ mentor.name }}</strong>
                <small>{{ mentor.lab_name }} · 剩余 {{ mentor.quota_left }}</small>
              </div>
              <el-button text type="danger" size="small" @click="toggleMentor(mentor)">移除</el-button>
            </div>
          </div>
          <p v-else class="muted">从左侧勾选最多 3 位导师；志愿不分先后。</p>

          <div class="obey-block">
            <div class="obey-row">
              <div>
                <strong>服从实训室内部调剂</strong>
                <small>在本实训室其他导师间调剂</small>
              </div>
              <el-switch v-model="obeyInternal" />
            </div>
            <div class="obey-row">
              <div>
                <strong>服从全院跨实训室调剂</strong>
                <small>允许被调剂到其他实训室</small>
              </div>
              <el-switch v-model="obeyCross" />
            </div>
          </div>

          <el-button type="primary" size="large" class="submit" :loading="saving" @click="submit">
            保存志愿
          </el-button>
          <p class="muted hint">提交后可在开放窗口内修改；截止后锁定，以最后一次提交为准。</p>
        </div>

        <div class="card">
          <div class="card-title">
            <h3>已保存志愿</h3>
            <span class="muted">{{ currentRoundName }}</span>
          </div>
          <div v-if="myIntentions.length" class="saved-list">
            <div v-for="item in myIntentions" :key="item.id" class="saved-item">
              <div class="saved-item__priority num">{{ item.priority }}</div>
              <div class="saved-item__info">
                <strong>{{ item.mentor_name }}</strong>
                <small>{{ item.lab_name }}</small>
              </div>
              <el-button text type="danger" size="small" @click="removeIntention(item)">撤回</el-button>
            </div>
          </div>
          <p v-else class="muted">当前轮次还没有保存的志愿。</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { metaApi, studentApi } from '../../api'
import PageHeader from '../../components/PageHeader.vue'
import { fmtDateTime, roundState } from '../../utils/format'

const loading = ref(true)
const saving = ref(false)
const labs = ref([])
const rounds = ref([])
const status = ref({ obey_internal: false, obey_cross: false })
const myIntentions = ref([])
const roundId = ref(null)
const selected = ref([])
const obeyInternal = ref(false)
const obeyCross = ref(false)

const intentionRounds = computed(() => rounds.value.filter((round) => round.kind === 'intention'))
const selectedRound = computed(() => intentionRounds.value.find((round) => round.id === roundId.value) || null)
const currentRoundName = computed(() => selectedRound.value?.name || '—')

const mentorIndex = computed(() => {
  const map = new Map()
  for (const lab of labs.value) {
    for (const mentor of lab.mentors || []) {
      map.set(mentor.id, { ...mentor, lab_id: lab.id, lab_name: lab.name })
    }
  }
  return map
})

const selectedMentors = computed(() =>
  selected.value.map((id) => mentorIndex.value.get(id)).filter(Boolean),
)

function isSelected(id) {
  return selected.value.includes(id)
}

function toggleMentor(mentor) {
  const index = selected.value.indexOf(mentor.id)
  if (index >= 0) {
    selected.value.splice(index, 1)
    return
  }
  if (selected.value.length >= 3) {
    ElMessage.warning('最多选择 3 个导师志愿')
    return
  }
  selected.value.push(mentor.id)
}

async function loadIntentions() {
  if (!roundId.value) {
    myIntentions.value = []
    selected.value = []
    return
  }
  myIntentions.value = await studentApi.intentions({ round_id: roundId.value })
  selected.value = myIntentions.value.map((item) => item.mentor_id)
}

async function submit() {
  if (!selectedRound.value) {
    ElMessage.warning('请选择填报轮次')
    return
  }
  if (!selected.value.length) {
    ElMessage.warning('请至少选择 1 个导师志愿')
    return
  }

  const names = selectedMentors.value.map((mentor) => mentor.name).join('、')
  await ElMessageBox.confirm(
    `将保存 ${selected.value.length} 个平行志愿：${names}。` +
      `服从内部调剂：${obeyInternal.value ? '是' : '否'}；服从全院跨室调剂：${obeyCross.value ? '是' : '否'}。` +
      '志愿不分先后，截止后锁定。',
    '确认提交志愿',
    { confirmButtonText: '确认提交', cancelButtonText: '再检查一下', type: 'warning' },
  )

  saving.value = true
  try {
    await studentApi.submitIntentions({
      mentor_ids: selected.value,
      round_id: roundId.value,
      obey_internal: obeyInternal.value,
      obey_cross: obeyCross.value,
    })
    ElMessage.success('志愿已保存')
    await loadIntentions()
  } finally {
    saving.value = false
  }
}

async function removeIntention(item) {
  await ElMessageBox.confirm(`撤回对「${item.mentor_name}」的志愿？`, '撤回志愿', {
    confirmButtonText: '撤回',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await studentApi.deleteIntention(item.id)
  ElMessage.success('已撤回')
  await loadIntentions()
}

watch(roundId, async () => {
  await loadIntentions()
})

onMounted(async () => {
  try {
    const [labData, roundData, statusData] = await Promise.all([
      metaApi.labs(),
      metaApi.rounds(),
      studentApi.status(),
    ])
    labs.value = labData
    rounds.value = roundData
    status.value = statusData
    obeyInternal.value = Boolean(statusData.obey_internal)
    obeyCross.value = Boolean(statusData.obey_cross)

    const candidates = roundData.filter((round) => round.kind === 'intention')
    const open = candidates.find((round) => round.is_open)
    const pick = open || candidates[candidates.length - 1] || candidates[0]
    if (pick) {
      roundId.value = pick.id
      await loadIntentions()
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.round-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 14px 18px;
}

.round-bar__left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.round-bar__time {
  font-size: 12px;
}

.intention-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 18px;
  align-items: start;
}

.lab-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.lab-head h3 {
  font-size: 16px;
}

.lab-head p {
  margin-top: 6px;
  font-size: 12.5px;
  line-height: 1.7;
}

.mentor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 12px;
}

.mentor-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border: 1.5px solid var(--tls-line);
  border-radius: 14px;
  background: #fbfdff;
  cursor: pointer;
  transition: all 0.16s ease;
}

.mentor-card:hover {
  border-color: #b9d2ee;
  background: #f5faff;
}

.mentor-card.is-selected {
  border-color: var(--tls-primary);
  background: linear-gradient(180deg, #fff 0%, #eef6ff 100%);
  box-shadow: 0 12px 26px rgba(47, 111, 186, 0.12);
}

.mentor-card.is-disabled {
  opacity: 0.55;
}

.mentor-card__top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mentor-card__check {
  pointer-events: none;
}

.mentor-card__name {
  display: flex;
  flex-direction: column;
  flex: 1;
  line-height: 1.3;
}

.mentor-card__name strong {
  font-size: 14.5px;
}

.mentor-card__name span {
  font-size: 11px;
}

.mentor-card__quota {
  color: var(--tls-primary-dark);
  font-size: 18px;
  font-weight: 800;
}

.mentor-card__quota small {
  color: var(--tls-muted);
  font-size: 11px;
  font-weight: 600;
}

.mentor-card__req {
  flex: 1;
  color: var(--tls-muted);
  font-size: 12px;
  line-height: 1.65;
}

.mentor-card__foot {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.selected-list,
.saved-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selected-item,
.saved-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--tls-line);
  border-radius: 12px;
  background: #f9fbff;
}

.selected-item div,
.saved-item__info {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 2px;
  min-width: 0;
}

.selected-item strong,
.saved-item strong {
  font-size: 13px;
}

.selected-item small,
.saved-item small {
  color: var(--tls-muted);
  font-size: 11.5px;
}

.saved-item__priority {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #e8f0fb;
  color: var(--tls-primary-dark);
  font-size: 12px;
  font-weight: 800;
}

.obey-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 16px 0;
  padding: 12px;
  border-radius: 12px;
  background: #f5f8fd;
}

.obey-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.obey-row div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.obey-row strong {
  font-size: 12.5px;
}

.obey-row small {
  color: var(--tls-muted);
  font-size: 11px;
}

.submit {
  width: 100%;
}

.hint {
  margin-top: 10px;
  font-size: 11.5px;
  line-height: 1.6;
}

@media (max-width: 1000px) {
  .intention-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .round-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .round-bar__left {
    flex-direction: column;
    align-items: flex-start;
    width: 100%;
  }

  .mentor-grid {
    grid-template-columns: 1fr;
  }
}
</style>
