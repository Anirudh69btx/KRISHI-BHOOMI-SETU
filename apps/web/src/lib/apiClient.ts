/**
 * FLIP v3.0 — API Client with Automatic Bearer Token Injection & Offline Mutation Queue (Segment 01)
 * Intercepts requests to append Keycloak access_token, handles 401 auto-renew,
 * and queues offline mutations into IndexedDB for Background Sync replay.
 */

import { getValidAccessToken, loginRedirect } from '../auth/oidc';
import { mutationQueue } from '../auth/idbStorage';

const BASE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
  skipAuth?: boolean;
  queueOffline?: boolean;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data: any,
  ) {
    super(data?.detail || statusText || `API Error ${status}`);
    this.name = 'ApiError';
  }
}

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { params, skipAuth = false, queueOffline = true, headers: customHeaders, ...fetchOptions } = options;
  const method = (fetchOptions.method || 'GET').toUpperCase();

  let url = endpoint.startsWith('http') ? endpoint : `${BASE_API_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    });
    const query = searchParams.toString();
    if (query) {
      url += (url.includes('?') ? '&' : '?') + query;
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  if (!skipAuth) {
    const token = await getValidAccessToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  // Check if offline and method is mutating (POST, PUT, DELETE)
  if (!navigator.onLine && queueOffline && ['POST', 'PUT', 'DELETE'].includes(method)) {
    console.warn(`[ApiClient] Device is offline. Queueing ${method} ${url} in IndexedDB mutation queue.`);
    const parsedBody = fetchOptions.body ? JSON.parse(fetchOptions.body as string) : undefined;
    const mutationId = await mutationQueue.queue(url, method as any, parsedBody, headers);
    return {
      _queued: true,
      mutationId,
      message: 'Operation queued for background synchronization when online.',
    } as unknown as T;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...fetchOptions,
      headers,
    });
  } catch (networkError: any) {
    // If fetch failed due to sudden network loss, queue mutating request
    if (queueOffline && ['POST', 'PUT', 'DELETE'].includes(method)) {
      console.warn(`[ApiClient] Network request failed. Queueing ${method} ${url} in IndexedDB.`);
      const parsedBody = fetchOptions.body ? JSON.parse(fetchOptions.body as string) : undefined;
      const mutationId = await mutationQueue.queue(url, method as any, parsedBody, headers);
      return {
        _queued: true,
        mutationId,
        message: 'Network offline. Operation queued for background sync.',
      } as unknown as T;
    }
    throw new ApiError(0, 'NetworkError', { detail: networkError?.message || 'Network request failed' });
  }

  // Handle 401 Unauthorized — Token expired or invalid
  if (response.status === 401 && !skipAuth) {
    console.warn('[ApiClient] 401 Unauthorized encountered. Redirecting to login...');
    await loginRedirect(window.location.pathname);
    throw new ApiError(401, 'Unauthorized', { detail: 'Session expired. Redirecting to login.' });
  }

  let responseData: any;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    responseData = await response.json();
  } else {
    responseData = await response.text();
  }

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText, responseData);
  }

  return responseData as T;
}

export const apiClient = {
  get: <T = any>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T = any>(endpoint: string, data?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T = any>(endpoint: string, data?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T = any>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),
};
