<template>
  <div class="login">
    <aside class="login__brand">
      <router-link to="/" class="brand">
        <span class="brand__mark">选</span>
        <span class="brand__text">
          <strong>实训室选组选拔</strong>
          <small>双向选择 · 分轮录取 · 统筹调剂</small>
        </span>
      </router-link>

      <div class="login__pitch">
        <h1>把选组流程<br />搬进一套系统</h1>
        <p>
          学生填报平行志愿，老师统一评分，管理员运行选拔并公示结果。
          名额、分数、确认、递补、调剂，全部可追溯。
        </p>
        <ul class="login__points">
          <li v-for="item in points" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div class="login__foot">
        <span class="pill pill--navy">3 种角色</span>
        <span>学生 · 老师 · 管理员</span>
      </div>
    </aside>

    <main class="login__main">
      <div class="login__card">
        <div class="login__head">
          <span class="eyebrow">欢迎回来</span>
          <h2>登录系统</h2>
          <p>请选择角色并输入账号，演示环境可使用下方一键填充。</p>
        </div>

        <div class="role-switch" role="tablist">
          <button
            v-for="item in roles"
            :key="item.value"
            type="button"
            class="role-switch__item"
            :class="{ active: role === item.value }"
            @click="switchRole(item.value)"
          >
            <el-icon :size="16"><component :is="item.icon" /></el-icon>
            {{ item.label }}
          </button>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
          <el-form-item label="账号" prop="student_no">
            <el-input v-model="form.student_no" size="large" placeholder="学号 / 工号 / 管理员账号" clearable>
              <template #prefix><el-icon><User /></el-icon></template>
            </el-input>
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              size="large"
              type="password"
              show-password
              placeholder="请输入密码"
              @keyup.enter="submit"
            >
              <template #prefix><el-icon><Lock /></el-icon></template>
            </el-input>
          </el-form-item>

          <el-button type="primary" size="large" class="login__submit" :loading="loading" native-type="submit">
            登录
          </el-button>
        </el-form>

        <div class="login__demo">
          <div>
            <strong>演示账号</strong>
            <span>{{ preset.hint }}</span>
          </div>
          <el-button text type="primary" @click="fillDemo">一键填入</el-button>
        </div>

        <div class="login__links">
          <router-link to="/">返回首页</router-link>
          <router-link to="/announcements">查看公示公告</router-link>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const DEMO_PASSWORD = 'demo-pass2026'

const roles = [
  { value: 'student', label: '学生', icon: 'User', hint: '学生 2023001 ~ 2023008 / ' + DEMO_PASSWORD, account: '2023001' },
  { value: 'mentor', label: '老师', icon: 'Avatar', hint: '老师 t1001 ~ t1007 / ' + DEMO_PASSWORD, account: 't1001' },
  { value: 'admin', label: '管理员', icon: 'Setting', hint: '管理员 admin / ' + DEMO_PASSWORD, account: 'admin' },
]

const role = ref('student')
const preset = computed(() => roles.find((item) => item.value === role.value) || roles[0])
const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  student_no: preset.value.account,
  password: DEMO_PASSWORD,
})

const rules = {
  student_no: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function switchRole(value) {
  role.value = value
  fillDemo()
}

function fillDemo() {
  form.student_no = preset.value.account
  form.password = DEMO_PASSWORD
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const session = await auth.login(form.student_no.trim(), form.password)
    ElMessage.success(`欢迎，${session.user.name}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    router.replace(redirect || auth.homePath)
  } finally {
    loading.value = false
  }
}

const points = [
  '最多 3 个平行志愿，不分先后',
  '统一四维面试评分，总分 100',
  '拟录取单意向自动确认、多意向唯一选择',
  '补录、调剂、公示、申诉全流程留痕',
]
</script>

<style scoped>
.login {
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  background:
    radial-gradient(900px 460px at 8% 0%, rgba(124, 111, 186, 0.2), transparent 58%),
    radial-gradient(760px 420px at 96% 12%, rgba(47, 111, 186, 0.16), transparent 60%),
    linear-gradient(180deg, #f5f8fe 0%, #eef2fb 100%);
}

.login__brand {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 32px;
  padding: 40px clamp(24px, 5vw, 64px);
  background:
    radial-gradient(560px 320px at 20% 10%, rgba(255, 255, 255, 0.14), transparent 60%),
    linear-gradient(155deg, #17324d 0%, #24486d 58%, #2f6fba 100%);
  color: #fff;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #fff;
}

.brand__mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  font-size: 19px;
  font-weight: 800;
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.brand__text strong {
  font-size: 16px;
}

.brand__text small {
  color: rgba(255, 255, 255, 0.72);
  font-size: 11px;
}

.login__pitch h1 {
  color: #fff;
  font-size: clamp(30px, 3.6vw, 46px);
  line-height: 1.16;
}

.login__pitch p {
  margin-top: 16px;
  max-width: 460px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
  line-height: 1.9;
}

.login__points {
  display: grid;
  gap: 10px;
  margin: 26px 0 0;
  padding: 0;
  list-style: none;
}

.login__points li {
  position: relative;
  padding-left: 20px;
  color: rgba(255, 255, 255, 0.88);
  font-size: 13px;
  line-height: 1.7;
}

.login__points li::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 8px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #f3a468;
}

.login__foot {
  display: flex;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}

.login__main {
  display: grid;
  place-items: center;
  padding: 40px 20px;
}

.login__card {
  width: min(440px, 100%);
  padding: 30px;
  border: 1px solid var(--tls-line);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 30px 70px rgba(23, 50, 77, 0.12);
  backdrop-filter: blur(12px);
}

.login__head h2 {
  margin-top: 8px;
  font-size: 26px;
}

.login__head p {
  margin-top: 8px;
  color: var(--tls-muted);
  font-size: 13px;
  line-height: 1.7;
}

.role-switch {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin: 22px 0 18px;
  padding: 4px;
  border-radius: 12px;
  background: #eef2f9;
}

.role-switch__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 6px;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: var(--tls-muted);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
}

.role-switch__item.active {
  background: #fff;
  color: var(--tls-primary-dark);
  box-shadow: 0 4px 12px rgba(23, 50, 77, 0.1);
}

.login__submit {
  width: 100%;
  margin-top: 4px;
}

.login__demo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 18px;
  padding: 12px 14px;
  border: 1px dashed #cfdcf0;
  border-radius: 12px;
  background: #f7faff;
}

.login__demo div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.login__demo strong {
  font-size: 12.5px;
  color: var(--tls-ink);
}

.login__demo span {
  color: var(--tls-muted);
  font-size: 11.5px;
  word-break: break-all;
}

.login__links {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 18px;
  font-size: 12.5px;
}

@media (max-width: 900px) {
  .login {
    grid-template-columns: 1fr;
  }

  .login__brand {
    padding: 22px 20px;
  }

  .login__pitch,
  .login__foot {
    display: none;
  }

  .login__main {
    padding: 24px 16px 40px;
  }
}

@media (max-width: 480px) {
  .login__card {
    padding: 22px;
    border-radius: 18px;
  }
}
</style>
