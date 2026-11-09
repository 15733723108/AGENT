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
        { path: 'home', name: 'Home', component: () => import('@/views/HomeView.vue'), meta: { title: '工作台' } },
        { path: 'chat/general', name: 'GeneralChat', component: () => import('@/views/GeneralChat.vue'), meta: { title: '通用问答' } },
        { path: 'chat/school', name: 'SchoolInfo', component: () => import('@/views/SchoolInfo.vue'), meta: { title: '学校信息问答' } },
        { path: 'lesson', name: 'LessonPlan', component: () => import('@/views/LessonPlan.vue'), meta: { title: '教案一键生成' } },
        { path: 'exam', name: 'ExamReview', component: () => import('@/views/ExamReview.vue'), meta: { title: '智能试卷研判' } },
        { path: 'library', name: 'Library', component: () => import('@/views/Library.vue'), meta: { title: '电子书 / 试卷' } },
        { path: 'kb', name: 'KnowledgeBase', component: () => import('@/views/KnowledgeBase.vue'), meta: { title: '知识库管理' } },
        { path: 'teacher-review', name: 'TeacherReview', component: () => import('@/views/TeacherReview.vue'), meta: { title: '教师审核' } },
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

// 同步浏览器标题：多标签页切换时更易辨识
const SITE_NAME = '劝学路小学智能体'
router.afterEach((to) => {
  const title = (to.meta.title as string | undefined) || (to.name as string | undefined)
  document.title = title ? `${title} · ${SITE_NAME}` : SITE_NAME
})

export default router
