import http from './http'

export const authApi = {
  login: (payload) => http.post('/auth/login', payload),
  loginDemo: () => http.post('/auth/login-demo'),
  me: () => http.get('/auth/me'),
}

export const metaApi = {
  labs: () => http.get('/meta/labs'),
  mentors: (params) => http.get('/meta/mentors', { params }),
  rounds: () => http.get('/meta/rounds'),
  publications: () => http.get('/publications'),
}

export const studentApi = {
  status: () => http.get('/student/status'),
  schedule: () => http.get('/student/schedule'),
  intentions: (params) => http.get('/student/intentions', { params }),
  submitIntentions: (payload) => http.post('/student/intentions', payload),
  deleteIntention: (id) => http.delete(`/student/intentions/${id}`),
  offers: () => http.get('/student/offers'),
  confirmOffer: (payload) => http.post('/student/offers/confirm-unique', payload),
  appeals: () => http.get('/student/appeals'),
  createAppeal: (payload) => http.post('/student/appeals', payload),
}

export const teacherApi = {
  profile: () => http.get('/teacher/profile'),
  applicants: () => http.get('/teacher/applicants'),
  interviews: (params) => http.get('/teacher/interviews', { params }),
  score: (payload) => http.post('/teacher/interviews', payload),
  offers: (params) => http.get('/teacher/offers', { params }),
}

export const adminApi = {
  dashboard: () => http.get('/admin/dashboard'),
  students: (params) => http.get('/admin/students', { params }),
  users: (params) => http.get('/auth/users', { params }),
  createUser: (payload) => http.post('/auth/users', payload),

  labs: () => http.get('/admin/labs'),
  createLab: (payload) => http.post('/admin/labs', payload),
  updateLab: (id, payload) => http.patch(`/admin/labs/${id}`, payload),
  deleteLab: (id) => http.delete(`/admin/labs/${id}`),

  mentors: (params) => http.get('/admin/mentors', { params }),
  createMentor: (payload) => http.post('/admin/mentors', payload),
  updateMentor: (id, payload) => http.patch(`/admin/mentors/${id}`, payload),
  deleteMentor: (id) => http.delete(`/admin/mentors/${id}`),

  rounds: () => http.get('/admin/rounds'),
  createRound: (payload) => http.post('/admin/rounds', payload),
  updateRound: (id, payload) => http.patch(`/admin/rounds/${id}`, payload),

  interviews: (params) => http.get('/admin/interviews', { params }),
  saveInterview: (payload) => http.post('/admin/interviews', payload),

  offers: (params) => http.get('/admin/offers', { params }),
  runSelection: (payload) => http.post('/admin/run-selection', payload),
  expireOffers: () => http.post('/admin/expire-offers'),
  fillVacancy: (mentorId, payload) => http.post(`/admin/fill-vacancy/${mentorId}`, payload),
  adjust: (payload) => http.post('/admin/adjust', payload),
  assignTalk: (payload) => http.post('/admin/assign-talk', payload),

  publications: () => http.get('/admin/publications'),
  createPublication: (payload) => http.post('/admin/publications', payload),
  publishPublication: (id) => http.post(`/admin/publications/${id}/publish`),

  appeals: (params) => http.get('/admin/appeals', { params }),
  handleAppeal: (id, payload) => http.post(`/admin/appeals/${id}/handle`, payload),

  enrollment: () => http.get('/admin/enrollment'),
  auditLogs: (params) => http.get('/admin/audit-logs', { params }),
}
