import { defineStore } from 'pinia'
import type { UserInfo } from '@/types'

interface UserState {
  token: string
  user: UserInfo | null
}

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    token: localStorage.getItem('czqxl_token') || '',
    user: localStorage.getItem('czqxl_user') ? JSON.parse(localStorage.getItem('czqxl_user')!) : null,
  }),
  getters: {
    isLogin: (s) => !!s.token,
    role: (s) => s.user?.role || '',
  },
  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem('czqxl_token', token)
    },
    setUser(user: UserInfo) {
      this.user = user
      localStorage.setItem('czqxl_user', JSON.stringify(user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('czqxl_token')
      localStorage.removeItem('czqxl_user')
    },
  },
})
