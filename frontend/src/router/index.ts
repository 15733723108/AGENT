import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layout/MainLayout.vue'),
      redirect: '/chat/general',
      children: [
        { path: 'chat/general', name: 'GeneralChat', component: () => import('@/views/GeneralChat.vue') },
        { path: 'chat/school', name: 'SchoolInfo', component: () => import('@/views/SchoolInfo.vue') },
        { path: 'lesson', name: 'LessonPlan', component: () => import('@/views/LessonPlan.vue') },
        { path: 'exam', name: 'ExamReview', component: () => import('@/views/ExamReview.vue') },
        { path: 'library', name: 'Library', component: () => import('@/views/Library.vue') },
        { path: 'kb', name: 'KnowledgeBase', component: () => import('@/views/KnowledgeBase.vue') },
        { path: 'teacher-review', name: 'TeacherReview', component: () => import('@/views/TeacherReview.vue') },
      ],
    },
  ],
})

const STUDENT_BLOCKED = ['/lesson', '/exam']
const ADMIN_ONLY = ['/kb', '/teacher-review']

router.beforeEach((to) => {
  const user = useUserStore()
  if (!to.meta.public && !user.token) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  const role = user.role
  if ((role === 'student' || role === 'parent') && STUDENT_BLOCKED.includes(to.path)) {
    return { path: '/chat/general' }
  }
  if (ADMIN_ONLY.includes(to.path) && role !== 'admin') {
    return { path: '/chat/general' }
  }
})

export default router
