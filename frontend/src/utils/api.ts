const API_BASE = 'http://localhost:8000/api';

interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  if (config.body && typeof config.body !== 'string') {
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(url, config);

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  // Handle unified backend envelope { code, message, data }
  const isEnvelope =
    payload &&
    typeof payload === 'object' &&
    'code' in payload &&
    'message' in payload &&
    'data' in payload;

  if (isEnvelope) {
    const envelope = payload as ApiEnvelope<T>;
    if (!response.ok || envelope.code !== 0) {
      throw new Error(envelope.message || `HTTP ${response.status}`);
    }
    return envelope.data;
  }

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      errorMessage = String((payload as { detail: unknown }).detail);
    }
    throw new Error(errorMessage);
  }

  return payload as T;
}
