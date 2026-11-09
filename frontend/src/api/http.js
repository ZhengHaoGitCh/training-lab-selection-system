import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000,
})

let authProvider = () => null

export function bindAuth(provider) {
  authProvider = provider
}

function handleUnauthorized() {
  const auth = authProvider()
  auth?.clear?.()
  if (!window.location.pathname.startsWith('/login')) {
    const current = `${window.location.pathname}${window.location.search}`
    window.location.assign(`/login?redirect=${encodeURIComponent(current)}`)
  }
}

http.interceptors.request.use((config) => {
  const auth = authProvider()
  if (auth?.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body.code === 'number') {
      if (body.code === 0) return body.data
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return body
  },
  (error) => {
    const status = error.response?.status
    const body = error.response?.data
    const message = body?.message || error.message || '网络异常，请稍后重试'
    if (status === 401 || body?.code === 2001) {
      handleUnauthorized()
    }
    ElMessage.error(message)
    return Promise.reject(new Error(message))
  },
)

export default http
