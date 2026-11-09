<template>
  <div class="page page--narrow">
    <PageHeader title="公示公告" subtitle="已发布的录取名单、补录、调剂与最终结果公示。" eyebrow="Public" />
    <div v-loading="loading">
      <div v-if="publications.length" class="stack">
        <article v-for="item in publications" :key="item.id" class="card notice" @click="open(item)">
          <div class="row">
            <span class="pill pill--green">已发布</span>
            <span class="spacer"></span>
            <span class="muted num">{{ fmtDateTime(item.published_at) }}</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.content || '点击查看正文' }}</p>
          <span class="notice__more">查看正文 →</span>
        </article>
      </div>
      <el-empty v-else-if="!loading" description="暂无已发布公示" />
    </div>

    <el-dialog v-model="visible" :title="active?.title" width="min(680px, 92vw)">
      <p class="muted num">发布于 {{ fmtDateTime(active?.published_at) }}</p>
      <div class="notice-body">{{ active?.content || '暂无正文' }}</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { metaApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import { fmtDateTime } from '../utils/format'

const publications = ref([])
const loading = ref(true)
const visible = ref(false)
const active = ref(null)

function open(item) {
  active.value = item
  visible.value = true
}

onMounted(async () => {
  try {
    publications.value = await metaApi.publications()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.notice {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.notice:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 38px rgba(23, 50, 77, 0.1);
}

.notice h3 {
  margin-top: 10px;
  font-size: 18px;
}

.notice p {
  margin-top: 8px;
  display: -webkit-box;
  overflow: hidden;
  color: var(--tls-muted);
  font-size: 13px;
  line-height: 1.8;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.notice__more {
  display: inline-block;
  margin-top: 12px;
  color: var(--tls-primary);
  font-size: 12.5px;
  font-weight: 600;
}

.notice-body {
  margin-top: 12px;
  color: var(--tls-ink-soft);
  line-height: 1.9;
  white-space: pre-wrap;
}
</style>
