import { create } from "zustand";
import apiClient from "../lib/apiClient";

export interface ApiKey { id: string; name: string; key_prefix: string; scopes: string[]; rate_limit_rps: number; is_active: boolean; expires_at: string | null; created_at: string; }

interface AuthState {
  token: null;
  user: { email: string } | null;
  apiKeys: ApiKey[];
  isAuthenticated: boolean;
  fetchUser: () => Promise<void>;
  fetchApiKeys: () => Promise<void>;
  createApiKey: (name: string) => Promise<{ key: string; record: ApiKey }>;
  revokeApiKey: (keyId: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(() => ({
  token: null,
  user: null,
  apiKeys: [],
  isAuthenticated: true,

  fetchUser: async () => {
    try { const r = await apiClient.get("/api/auth/me"); useAuthStore.setState({ user: r.data }); } catch {}
  },

  fetchApiKeys: async () => {
    try { const r = await apiClient.get("/api/auth/api-keys"); useAuthStore.setState({ apiKeys: r.data }); } catch {}
  },

  createApiKey: async (name: string) => {
    const r = await apiClient.post("/api/auth/api-keys", { name });
    const record = r.data;
    useAuthStore.setState((s) => ({ apiKeys: [...s.apiKeys, record] }));
    return { key: "adpulse-demo-" + record.id.slice(0, 8), record };
  },

  revokeApiKey: async (keyId: string) => {
    await apiClient.delete(`/api/auth/api-keys/${keyId}`);
    useAuthStore.setState((s) => ({ apiKeys: s.apiKeys.filter((k) => k.id !== keyId) }));
  },

  logout: () => {},
}));

export default useAuthStore;
