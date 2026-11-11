import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    name: 'landing',
    component: () => import('../views/LandingView.vue'),
    meta: { public: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true, bare: true },
  },
  {
    path: '/announcements',
    name: 'announcements',
    component: () => import('../views/AnnouncementsView.vue'),
    meta: { public: true },
  },
  {
    path: '/forbidden',
    name: 'forbidden',
    component: () => import('../views/ForbiddenView.vue'),
    meta: { public: true },
  },
  {
    path: '/student',
    name: 'student-home',
    component: () => import('../views/student/StudentHomeView.vue'),
    meta: { roles: ['student'] },
  },
  {
    path: '/student/intentions',
    name: 'student-intentions',
    component: () => import('../views/student/IntentionsView.vue'),
    meta: { roles: ['student'] },
  },
  {
    path: '/student/offers',
    name: 'student-offers',
    component: () => import('../views/student/OffersView.vue'),
    meta: { roles: ['student'] },
  },
  {
    path: '/student/appeals',
    name: 'student-appeals',
    component: () => import('../views/student/AppealsView.vue'),
    meta: { roles: ['student'] },
  },
  {
    path: '/teacher',
    name: 'teacher-home',
    component: () => import('../views/teacher/TeacherHomeView.vue'),
    meta: { roles: ['mentor'] },
  },
  {
    path: '/teacher/applicants',
    name: 'teacher-applicants',
    component: () => import('../views/teacher/ApplicantsView.vue'),
    meta: { roles: ['mentor'] },
  },
  {
    path: '/teacher/offers',
    name: 'teacher-offers',
    component: () => import('../views/teacher/OffersView.vue'),
    meta: { roles: ['mentor'] },
  },
  {
    path: '/admin',
    name: 'admin-dashboard',
    component: () => import('../views/admin/DashboardView.vue'),
    meta: { roles: ['admin'] },
  },
  {
    path: '/admin/labs',
    name: 'admin-labs',
    component: () => import('../views/admin/LabsView.vue'),
    meta: { roles: ['admin'] },
  },
  {
    path: '/admin/rounds',
    name: 'admin-rounds',
    component: () => import('../views/admin/RoundsView.vue'),
    meta: { roles: ['admin'] },
  },
  {
    path: '/admin/interviews',
    name: 'admin-interviews',
    component: () => import('../views/admin/InterviewsView.vue'),
    meta: { roles: ['admin'] },
  },
  {
    path: '/admin/selection',
    name: 'admin-selection',
    component: () => import('../views/admin/SelectionView.vue'),
    meta: { roles: ['admin'] },
  },
  {
    path: '/admin/publications',
    name: 'admin-publications',
    component: () => import('../views/admin/PublicationsView.vue'),
    meta: { roles: ['admin'] },
  },
  {
    path: '/admin/audit',
    name: 'admin-audit',
    component: () => import('../views/admin/AuditView.vue'),
    meta: { roles: ['admin'] },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: { public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.roles) {
    if (!auth.isLoggedIn) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (!to.meta.roles.includes(auth.role)) {
      return { name: 'forbidden', query: { from: to.fullPath } }
    }
  }

  if (to.name === 'login' && auth.isLoggedIn) {
    return auth.homePath
  }

  return true
})

export default router
