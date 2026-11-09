<template>
  <div class="page-header">
    <div class="page-header__text">
      <div v-if="eyebrow" class="eyebrow">{{ eyebrow }}</div>
      <h1>{{ title }}</h1>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.default" class="page-header__actions">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  eyebrow: { type: String, default: '' },
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 22px;
}

.page-header h1 {
  font-size: clamp(22px, 2.6vw, 30px);
  line-height: 1.25;
}

.page-header p {
  margin-top: 8px;
  max-width: 760px;
  color: var(--tls-muted);
  font-size: 14px;
  line-height: 1.7;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

@media (max-width: 768px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .page-header__actions {
    width: 100%;
  }
}
</style>
