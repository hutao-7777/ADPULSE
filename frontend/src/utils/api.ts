import apiClient from '../lib/apiClient';

interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
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
}
