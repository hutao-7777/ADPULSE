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

      try {
        if (!refreshPromise) {
          refreshPromise = useAuthStore.getState().refresh();
        }
        const newToken = await refreshPromise;
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
