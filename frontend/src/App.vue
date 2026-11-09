<template>
  <router-view v-slot="{ Component }">
    <component :is="Component" v-if="$route.meta.bare" />
    <AppShell v-else>
      <component :is="Component" />
    </AppShell>
  </router-view>
</template>

<script setup>
import AppShell from './layouts/AppShell.vue'
</script>
