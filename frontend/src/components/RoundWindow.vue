<template>
  <div v-if="round" class="round-window">
    <div class="round-window__head">
      <span class="pill" :class="`pill--${tone}`">{{ kindText }}</span>
      <span class="round-window__state" :class="`is-${state.key}`">{{ state.text }}</span>
    </div>
    <strong class="round-window__name">{{ round.name }}</strong>
    <span class="time-badge num">
      {{ fmtDateTime(round.starts_at) }} ~ {{ fmtDateTime(round.ends_at) }}
    </span>
  </div>
  <div v-else class="round-window round-window--empty muted">暂无轮次</div>
</template>

<script setup>
import { computed } from 'vue'
import { ROUND_KIND_TEXT, ROUND_KIND_TONE, fmtDateTime, roundState } from '../utils/format'

const props = defineProps({
  round: { type: Object, default: null },
})

const kindText = computed(() => ROUND_KIND_TEXT[props.round?.kind] || '轮次')
const tone = computed(() => ROUND_KIND_TONE[props.round?.kind] || 'blue')
const state = computed(() => roundState(props.round))
</script>

<style scoped>
.round-window {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.round-window__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.round-window__state {
  font-size: 12px;
  font-weight: 700;
  color: var(--tls-muted);
}

.round-window__state.is-open {
  color: var(--tls-green);
}

.round-window__state.is-upcoming {
  color: var(--tls-accent);
}

.round-window__name {
  font-size: 15px;
  color: var(--tls-ink);
}

.round-window--empty {
  font-size: 13px;
}
</style>
