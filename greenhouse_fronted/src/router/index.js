import { createRouter, createWebHistory } from 'vue-router'
import IndexPage from '../views/IndexPage.vue'
import ControlPage from '../views/ControlPage.vue'
import HistoryPage from '../views/HistoryPage.vue'
import LoginPage from '../views/LoginPage.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginPage
  },
  {
    path: '/',
    name: 'Index',
    component: IndexPage,
    meta: { requiresAuth: true }
  },
  {
    path: '/control',
    name: 'Control',
    component: ControlPage,
    meta: { requiresAuth: true }
  },
  {
    path: '/history',
    name: 'History',
    component: HistoryPage,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 导航守卫：未登录用户重定向到登录页
router.beforeEach((to, from, next) => {
  const currentUser = localStorage.getItem('greenhouse_current_user')
  if (to.meta.requiresAuth && !currentUser) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router