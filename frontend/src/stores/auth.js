import { defineStore } from 'pinia'
import http from '../api/http'
import { ROLE_TEXT } from '../utils/format'

const TOKEN_KEY = 'tls_token'
const USER_KEY = 'tls_user'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: readUser(),
  }),
  getters: {
    role: (state) => state.user?.role || '',
    isLoggedIn: (state) => Boolean(state.token && state.user),
    isStudent: (state) => state.user?.role === 'student',
    isTeacher: (state) => state.user?.role === 'mentor',
    isAdmin: (state) => state.user?.role === 'admin',
    isStaff: (state) => ['admin', 'auditor'].includes(state.user?.role),
    displayName: (state) => state.user?.name || state.user?.student_no || '访客',
    roleText: (state) => ROLE_TEXT[state.user?.role] || '',
    homePath: (state) => {
      const role = state.user?.role
      if (role === 'student') return '/student'
      if (role === 'mentor') return '/teacher'
      if (role === 'admin' || role === 'auditor') return '/admin'
      return '/'
    },
  },
  actions: {
    setSession(payload) {
      this.token = payload.access_token
      this.user = payload.user
      localStorage.setItem(TOKEN_KEY, this.token)
      localStorage.setItem(USER_KEY, JSON.stringify(this.user))
    },
    clear() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
    async login(studentNo, password) {
      const data = await http.post('/auth/login', { student_no: studentNo, password })
      this.setSession(data)
      return data
    },
    async loginDemo(kind = 'student') {
      const data = await http.post('/auth/login-demo')
      const session = data[kind] || data.student || data.admin
      if (!session) throw new Error('演示账号未初始化，请先运行 seed.py')
      this.setSession(session)
      return session
    },
    async refreshMe() {
      const user = await http.get('/auth/me')
      this.user = user
      localStorage.setItem(USER_KEY, JSON.stringify(user))
      return user
    },
  },
})
