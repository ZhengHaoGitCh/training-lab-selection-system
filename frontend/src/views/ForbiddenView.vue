<template>
  <div class="page page--narrow state-page">
    <div class="card state-card">
      <span class="state-card__code">403</span>
      <h1>没有访问权限</h1>
      <p>
        当前账号角色为
        <strong>{{ auth.roleText || '访客' }}</strong>
        ，不能访问该页面。学生、老师、管理员分别拥有独立的工作台。
      </p>
      <div class="hero-actions">
        <el-button type="primary" @click="$router.push(auth.isLoggedIn ? auth.homePath : '/login')">
          {{ auth.isLoggedIn ? '回到我的首页' : '去登录' }}
        </el-button>
        <el-button @click="$router.push('/')">返回首页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
</script>

<style scoped>
.state-page {
  display: grid;
  min-height: 62vh;
  place-items: center;
}

.state-card {
  width: min(620px, 100%);
  padding: 40px;
  text-align: center;
}

.state-card__code {
  color: #d7e1f1;
  font-size: 84px;
  font-weight: 900;
  line-height: 1;
}

.state-card h1 {
  margin-top: 8px;
  font-size: 26px;
}

.state-card p {
  margin-top: 12px;
  color: var(--tls-muted);
  line-height: 1.8;
}

.state-card .hero-actions {
  justify-content: center;
  margin-top: 26px;
}
</style>
