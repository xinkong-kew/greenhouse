import { createRouter, createWebHistory } from 'vue-router'
import IndexPage from '../views/IndexPage.vue'
import ControlPage from '../views/ControlPage.vue'
import HistoryPage from '../views/HistoryPage.vue'

const routes = [
  {
    path: '/',
    name: 'Index',
    component: IndexPage
  },
  {
    path: '/control',
    name: 'Control',
    component: ControlPage
  },
  {
    path: '/history',
    name: 'History',
    component: HistoryPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router