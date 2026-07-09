import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import apiClient from '../lib/apiClient';

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_rps: number;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  apiKeys: ApiKey[];
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<string | null>;
  fetchUser: () => Promise<void>;
  fetchApiKeys: () => Promise<void>;
  createApiKey: (name: string) => Promise<{ key: string; record: ApiKey }>;
  revokeApiKey: (id: string) => Promise<void>;
}

const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      apiKeys: [],
      isAuthenticated: false,

      login: async (email, password) => {
        const { data } = await apiClient.post('/auth/login', {
          email,
          password,
        });
        const { access_token, refresh_token } = data.data;
        set({
          token: access_token,
          refreshToken: refresh_token,
          isAuthenticated: true,
        });
        await get().fetchUser();
      },

      register: async (email, password) => {
        await apiClient.post('/auth/register', { email, password });
        await get().login(email, password);
      },

      logout: () => {
        set({
          token: null,
          refreshToken: null,
          user: null,
          apiKeys: [],
          isAuthenticated: false,
        });
      },

      refresh: async () => {
        const currentRefresh = get().refreshToken;
        if (!currentRefresh) {
          get().logout();
          return null;
        }
        try {
          const { data } = await apiClient.post('/auth/refresh', {
            refresh_token: currentRefresh,
          });
          const { access_token } = data.data;
          set({ token: access_token, isAuthenticated: true });
          return access_token;
        } catch {
          get().logout();
          return null;
        }
      },

      fetchUser: async () => {
        const { data } = await apiClient.get('/auth/me');
        set({ user: data.data });
      },

      fetchApiKeys: async () => {
        const { data } = await apiClient.get('/auth/api-keys');
        set({ apiKeys: data.data });
      },

      createApiKey: async (name: string) => {
        const { data } = await apiClient.post('/auth/api-keys', {
          name,
          scopes: ['rtb:write'],
        });
        await get().fetchApiKeys();
        return { key: data.data.key, record: data.data };
      },

      revokeApiKey: async (id: string) => {
        await apiClient.delete(`/auth/api-keys/${id}`);
        await get().fetchApiKeys();
      },
    }),
    {
      name: 'adpulse-auth',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;
