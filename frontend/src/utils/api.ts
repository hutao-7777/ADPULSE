import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import useAuthStore from '../stores/authStore';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().token;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
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
      const newToken = await useAuthStore.getState().refresh();
      if (newToken && originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      }
      window.location.href = '/login';
    }

    return Promise.reject(error);
  }
);

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
  return '请求失败';
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

export default apiClient;
