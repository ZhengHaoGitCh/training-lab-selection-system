<template>
  <div class="page page--narrow state-page">
    <div class="card state-card">
      <span class="state-card__code">404</span>
      <h1>页面不存在</h1>
      <p>链接可能已失效，或该页面尚未实现。可以从首页继续浏览流程。</p>
      <div class="hero-actions">
        <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
      </div>
    </div>
  </div>
</template>

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
