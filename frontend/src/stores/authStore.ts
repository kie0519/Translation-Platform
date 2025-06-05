import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authService } from '@/services/authService';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  is_verified: boolean;
  is_premium: boolean;
  translation_count: number;
  words_translated: number;
  preferred_source_lang: string;
  preferred_target_lang: string;
  preferred_engine: string;
  created_at: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  
  // Actions
  login: (username: string, password: string) => Promise<void>;
  register: (userData: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
  updateUser: (userData: Partial<User>) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isLoading: false,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        try {
          set({ isLoading: true });
          
          const response = await authService.login(username, password);
          
          set({
            user: response.user,
            token: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
          
          // 设置axios默认header
          authService.setAuthToken(response.access_token);
          
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (userData) => {
        try {
          set({ isLoading: true });
          
          const user = await authService.register(userData);
          
          set({
            user,
            isLoading: false,
          });
          
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        authService.logout();
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      refreshAuth: async () => {
        try {
          const { refreshToken } = get();
          if (!refreshToken) {
            throw new Error('No refresh token available');
          }
          
          const response = await authService.refreshToken(refreshToken);
          
          set({
            token: response.access_token,
            refreshToken: response.refresh_token,
          });
          
          authService.setAuthToken(response.access_token);
          
        } catch (error) {
          // 刷新失败，清除认证状态
          get().logout();
          throw error;
        }
      },

      updateUser: (userData) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...userData } : null,
        }));
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // 恢复时设置认证token
        if (state?.token) {
          authService.setAuthToken(state.token);
        }
      },
    }
  )
);