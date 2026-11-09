<template>
  <div class="stat-card" :class="`stat-card--${tone}`">
    <div class="stat-card__label">{{ label }}</div>
    <div class="stat-card__value num">
      {{ value }}<small v-if="suffix">{{ suffix }}</small>
    </div>
    <div v-if="hint" class="stat-card__hint">{{ hint }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  suffix: { type: String, default: '' },
  hint: { type: String, default: '' },
  tone: { type: String, default: 'blue' },
})
</script>

<style scoped>
.stat-card {
  position: relative;
  overflow: hidden;
  padding: 16px 18px;
  border: 1px solid var(--tls-line);
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(23, 50, 77, 0.05);
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--tls-primary);
}

.stat-card--green::before {
  background: var(--tls-green);
}

.stat-card--orange::before {
  background: var(--tls-accent);
}

.stat-card--navy::before {
  background: var(--tls-ink);
}

.stat-card--muted::before {
  background: #9aa9bd;
}

.stat-card__label {
  color: var(--tls-muted);
  font-size: 13px;
  font-weight: 600;
}

.stat-card__value {
  margin-top: 8px;
  font-size: 30px;
  font-weight: 800;
  line-height: 1.1;
  color: var(--tls-ink);
}

.stat-card__value small {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--tls-muted);
}

.stat-card__hint {
  margin-top: 8px;
  color: var(--tls-muted);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 768px) {
  .stat-card {
    padding: 14px;
  }

  .stat-card__value {
    font-size: 24px;
  }
}
</style>
