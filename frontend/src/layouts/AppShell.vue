<template>
  <div class="shell">
    <header class="header">
      <div class="header__inner">
        <router-link to="/" class="brand">
          <span class="brand__mark">选</span>
          <span class="brand__text">
            <strong>实训室选组选拔</strong>
            <small>双向选择 · 分轮录取 · 统筹调剂</small>
          </span>
        </router-link>

        <nav class="nav">
          <el-menu
            :default-active="activePath"
            mode="horizontal"
            router
            :ellipsis="true"
            class="nav__menu"
          >
            <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
              {{ item.label }}
            </el-menu-item>
          </el-menu>
        </nav>

        <div class="header__right">
          <template v-if="auth.isLoggedIn">
            <el-dropdown trigger="click" @command="onCommand">
              <button class="user-chip" type="button">
                <span class="user-chip__avatar">{{ avatarText }}</span>
                <span class="user-chip__meta">
                  <strong>{{ auth.displayName }}</strong>
                  <small>{{ auth.roleText }}</small>
                </span>
                <el-icon><ArrowDown /></el-icon>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="home">我的首页</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button type="primary" @click="$router.push('/login')">登录</el-button>
          </template>
          <button class="burger" type="button" aria-label="打开菜单" @click="drawer = true">
            <el-icon :size="22"><Menu /></el-icon>
          </button>
        </div>
      </div>
    </header>

    <main class="shell__main">
      <slot />
    </main>

    <footer class="footer">
      <div class="footer__inner">
        <span>实训室选组选拔系统 · 课程演示版</span>
        <span class="muted">FastAPI + Vue 3 · 双向选择 / 分轮录取 / 统筹调剂</span>
      </div>
    </footer>

    <el-drawer v-model="drawer" direction="rtl" size="272px" title="导航">
      <div class="drawer-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="drawer-nav__item"
          :class="{ active: activePath === item.path }"
          @click="drawer = false"
        >
          {{ item.label }}
        </router-link>
        <router-link
          v-if="auth.isLoggedIn"
          :to="auth.homePath"
          class="drawer-nav__item"
          @click="drawer = false"
        >
          我的首页
        </router-link>
        <router-link
          v-else
          to="/login"
          class="drawer-nav__item"
          @click="drawer = false"
        >
          登录
        </router-link>
        <button
          v-if="auth.isLoggedIn"
          type="button"
          class="drawer-nav__item drawer-nav__logout"
          @click="logout"
        >
          退出登录
        </button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const drawer = ref(false)

const studentNav = [
  { path: '/student', label: '我的选组' },
  { path: '/student/intentions', label: '志愿填报' },
  { path: '/student/offers', label: '拟录取' },
  { path: '/student/appeals', label: '我的申诉' },
]

const teacherNav = [
  { path: '/teacher', label: '工作台' },
  { path: '/teacher/applicants', label: '报名学生' },
  { path: '/teacher/offers', label: '我的名单' },
]

const adminNav = [
  { path: '/admin', label: '仪表盘' },
  { path: '/admin/labs', label: '实训室' },
  { path: '/admin/rounds', label: '轮次' },
  { path: '/admin/interviews', label: '面试' },
  { path: '/admin/selection', label: '选拔录取' },
  { path: '/admin/publications', label: '公示申诉' },
  { path: '/admin/audit', label: '审计' },
]

const guestNav = [
  { path: '/', label: '首页' },
  { path: '/announcements', label: '公示公告' },
]

const navItems = computed(() => {
  if (!auth.isLoggedIn) return guestNav
  if (auth.isStudent) return studentNav
  if (auth.isTeacher) return teacherNav
  if (auth.isStaff) return adminNav
  return guestNav
})

const activePath = computed(() => route.path)
const avatarText = computed(() => auth.displayName.slice(0, 1))

function onCommand(command) {
  if (command === 'home') {
    router.push(auth.homePath)
  } else if (command === 'logout') {
    logout()
  }
}

function logout() {
  auth.clear()
  drawer.value = false
  router.push('/')
}
</script>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
}

.header {
  position: sticky;
  top: 0;
  z-index: 30;
  border-bottom: 1px solid rgba(223, 230, 242, 0.9);
  background: rgba(248, 250, 254, 0.86);
  backdrop-filter: blur(14px);
}

.header__inner {
  display: flex;
  align-items: center;
  gap: 18px;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 10px 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  color: var(--tls-ink);
}

.brand__mark {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(145deg, #17324d, #2f6fba);
  color: #fff;
  font-size: 18px;
  font-weight: 800;
  box-shadow: 0 8px 18px rgba(23, 50, 77, 0.26);
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.brand__text strong {
  font-size: 15px;
  letter-spacing: 0.02em;
}

.brand__text small {
  color: var(--tls-muted);
  font-size: 11px;
}

.nav {
  flex: 1;
  min-width: 0;
}

.nav__menu {
  border-bottom: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: #e9f0fb;
  --el-menu-active-color: var(--tls-primary-dark);
  --el-menu-text-color: var(--tls-ink-soft);
}

.nav__menu :deep(.el-menu-item) {
  height: 46px;
  padding: 0 13px;
  font-size: 13.5px;
  font-weight: 600;
  border-radius: 10px;
}

.nav__menu :deep(.el-menu-item.is-active) {
  background: #e8f0fb;
}

.header__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 10px 6px 6px;
  border: 1px solid var(--tls-line);
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
  color: var(--tls-ink);
}

.user-chip__avatar {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--tls-ink);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}

.user-chip__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.2;
}

.user-chip__meta strong {
  font-size: 12.5px;
}

.user-chip__meta small {
  color: var(--tls-muted);
  font-size: 11px;
}

.burger {
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid var(--tls-line);
  border-radius: 10px;
  background: #fff;
  color: var(--tls-ink);
  cursor: pointer;
}

.shell__main {
  flex: 1;
}

.footer {
  border-top: 1px solid rgba(223, 230, 242, 0.8);
  background: rgba(255, 255, 255, 0.55);
}

.footer__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 18px 24px;
  color: var(--tls-muted);
  font-size: 12px;
}

.drawer-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.drawer-nav__item {
  padding: 12px 14px;
  border-radius: 10px;
  color: var(--tls-ink-soft);
  font-size: 14px;
  font-weight: 600;
  text-align: left;
  background: transparent;
  border: none;
  cursor: pointer;
}

.drawer-nav__item.active,
.drawer-nav__item:hover {
  background: #e8f0fb;
  color: var(--tls-primary-dark);
}

.drawer-nav__logout {
  margin-top: 8px;
  color: #c0392b;
}

@media (max-width: 1000px) {
  .nav {
    display: none;
  }

  .burger {
    display: inline-flex;
  }

  .header__inner {
    justify-content: space-between;
    padding: 10px 16px;
  }
}

@media (max-width: 620px) {
  .brand__text small {
    display: none;
  }

  .user-chip__meta {
    display: none;
  }

  .footer__inner {
    flex-direction: column;
    align-items: flex-start;
    padding: 16px;
  }
}
</style>
