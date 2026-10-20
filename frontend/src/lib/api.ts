const BASE_URL = '/api/v1';

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string = 'API_ERROR', status: number = 400) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

async function refreshToken(): Promise<string | null> {
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    if (res.ok) {
      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem('skillissue_token', data.access_token);
        return data.access_token;
      }
    }
  } catch {
    // Refresh failed
  }
  return null;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  let token = localStorage.getItem('skillissue_token');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  // Handle FormData where Content-Type is set automatically by browser
  if (options.body instanceof FormData) {
    delete (headers as Record<string, string>)['Content-Type'];
  }

  let response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers,
  });

  // Attempt automatic refresh on 401 if we have an active session
  if (response.status === 401 && !endpoint.startsWith('/auth/login') && !endpoint.startsWith('/auth/refresh')) {
    const newToken = await refreshToken();
    if (newToken) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`;
      response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        credentials: 'include',
        headers,
      });
    }
  }

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401 && !endpoint.startsWith('/auth/login')) {
      localStorage.removeItem('skillissue_token');
      localStorage.removeItem('skillissue_user');
      window.dispatchEvent(new CustomEvent('auth:expired'));
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        window.location.href = '/login';
      }
    }
    const message = data?.error?.message || data?.detail || 'An unexpected error occurred';
    const code = data?.error?.code || 'REQUEST_FAILED';
    throw new ApiError(message, code, response.status);
  }

  return data as T;
}


export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
  post: <T>(endpoint: string, body?: any) =>
    request<T>(endpoint, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
  put: <T>(endpoint: string, body?: any) =>
    request<T>(endpoint, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(endpoint: string, body?: any) =>
    request<T>(endpoint, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
};
