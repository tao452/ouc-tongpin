import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue')
    },
    {
      path: '/review',
      name: 'Review',
      component: () => import('../views/Review.vue')
    },
    {
      path: '/heatmap',
      name: 'Heatmap',
      component: () => import('../views/Heatmap.vue')
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue')
    }
  ]
})

export default router
