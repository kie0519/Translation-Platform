import axios from 'axios';
import { User } from '@/stores/authStore';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// 创建axios实例
const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth-token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh-token');
        if (refreshToken) {
          const response = await authService.refreshToken(refreshToken);
          authService.setAuthToken(response.access_token);
          return api(originalRequest);
        }
      } catch (refreshError) {
        // 刷新失败，跳转到登录页
        authService.logout();
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

class AuthService {
  setAuthToken(token: string) {
    localStorage.setItem('auth-token', token);
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  removeAuthToken() {
    localStorage.removeItem('auth-token');
    localStorage.removeItem('refresh-token');
    delete api.defaults.headers.common['Authorization'];
  }

  async login(username: string, password: string): Promise<LoginResponse> {
    try {
      const response = await api.post('/auth/login', {
        username,
        password,
      });
      
      const { access_token, refresh_token } = response.data;
      
      // 保存tokens
      this.setAuthToken(access_token);
      localStorage.setItem('refresh-token', refresh_token);
      
      // 获取用户信息
      const userResponse = await api.get('/users/me');
      
      return {
        ...response.data,
        user: userResponse.data,
      };
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '登录失败');
    }
  }

  async register(userData: RegisterData): Promise<User> {
    try {
      const response = await api.post('/auth/register', userData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '注册失败');
    }
  }

  async refreshToken(refreshToken: string): Promise<{ access_token: string; refresh_token: string }> {
    try {
      const response = await api.post('/auth/refresh', {
        refresh_token: refreshToken,
      });
      
      const { access_token, refresh_token: newRefreshToken } = response.data;
      
      // 更新tokens
      this.setAuthToken(access_token);
      localStorage.setItem('refresh-token', newRefreshToken);
      
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '令牌刷新失败');
    }
  }

  async logout() {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      // 忽略登出错误
    } finally {
      this.removeAuthToken();
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      const response = await api.get('/users/me');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '获取用户信息失败');
    }
  }

  async updateProfile(userData: Partial<User>): Promise<User> {
    try {
      const response = await api.put('/users/me', userData);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '更新用户信息失败');
    }
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    try {
      await api.post('/users/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || '修改密码失败');
    }
  }
}

export const authService = new AuthService();
export { api };