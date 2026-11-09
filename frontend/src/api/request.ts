import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

/**
 * 响应拦截器直接返回 resp.data，所以调用方拿到的是业务数据 T，
 * 而不是 AxiosResponse<T>。axios 自身类型无法表达这一点，
 * 这里显式声明实例签名，避免所有 api 模块被推断成 AxiosResponse。
 */
interface DataRequest {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = any>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  put<T = any>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  patch<T = any>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  interceptors: AxiosInstance['interceptors']
}

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 120000,
}) as unknown as DataRequest

request.interceptors.request.use((config) => {
  const user = useUserStore()
  if (user.token) {
    config.headers.Authorization = `Bearer ${user.token}`
  }
  return config
})

request.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const status = error.response?.status
    if (status === 401) {
      const user = useUserStore()
      user.logout()
      ElMessage.error('登录已过期，请重新登录')
    } else {
      ElMessage.error(error.response?.data?.detail || error.message || '请求失败')
    }
    return Promise.reject(error)
  },
)

export default request
