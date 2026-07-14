import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

import useAuthStore from '../stores/authStore';
import { useDataSourceStore } from '../stores/dataSourceStore';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

let refreshPromise: Promise<string | null> | null = null;

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().token;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (config.method?.toLowerCase() === 'get' && config.url) {
    // Do not append data_source to the available-sources endpoint itself,
    // otherwise we would only see the currently selected source.
    if (config.url.includes('/dashboard/available-sources')) {
      return config;
    }
    const source = useDataSourceStore.getState().activeSource;
    if (source && source !== 'all') {
      config.params = { ...config.params, data_source: source };
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const body = response.data;
    if (body && typeof body === 'object' && 'code' in body && 'data' in body) {
      if (body.code !== 0) {
        return Promise.reject(new Error(body.message || `API error ${body.code}`));
      }
      response.data = body.data;
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;

      try {
        if (!refreshPromise) {
          refreshPromise = Promise.resolve(null);
        }
        const newToken = await Promise.resolve(null);
        refreshPromise = null;

        if (newToken && originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        }
      } catch {
        refreshPromise = null;
      }

      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// ------------------------------------------------------------------
// Unified request helper (moved from utils/api.ts)
// ------------------------------------------------------------------

interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { message?: string; detail?: string }
      | undefined;
    if (data?.message) return data.message;
    if (data?.detail) return data.detail;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'Request failed';
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || 'GET').toUpperCase();
  const body =
    options.body && typeof options.body === 'string'
      ? JSON.parse(options.body)
      : options.body;

  try {
    const response = await apiClient.request<ApiEnvelope<T>>({
      url: endpoint,
      method,
      data: method === 'GET' ? undefined : body,
      headers: options.headers as Record<string, string>,
    });

    const payload = response.data;

    const isEnvelope =
      payload &&
      typeof payload === 'object' &&
      'code' in payload &&
      'message' in payload &&
      'data' in payload;

    if (isEnvelope) {
      if (payload.code !== 0) {
        throw new Error(payload.message || `API error ${payload.code}`);
      }
      return payload.data;
    }

    return payload as unknown as T;
  } catch (error) {
    const wrapped = new Error(extractErrorMessage(error));
    (wrapped as Error & { cause?: unknown }).cause = error;
    throw wrapped;
  }
}