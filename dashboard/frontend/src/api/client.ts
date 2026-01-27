/**
 * API client for Thanos Dashboard backend.
 *
 * Provides typed functions to fetch data from the FastAPI backend.
 * Base URL defaults to localhost:8001 but can be configured via env var.
 */

import type {
  ApiResponse,
  TasksData,
  TodayMetrics,
  EnergyData,
  HealthData,
  CorrelationData,
  ApiError,
} from '../types';

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

// ============================================================================
// Fetch Helpers
// ============================================================================

/**
 * Generic fetch wrapper with error handling and type safety.
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
        status: response.status,
      }));
      throw new Error(error.detail || `Request failed with status ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unknown error occurred while fetching data');
  }
}

// ============================================================================
// Tasks API
// ============================================================================

export interface GetTasksParams {
  status?: 'active' | 'queued' | 'backlog' | 'done';
  clientId?: number;
  clientName?: string;
  limit?: number;
}

/**
 * Fetch tasks from WorkOS with optional filters.
 */
export async function getTasks(params?: GetTasksParams): Promise<TasksData> {
  const searchParams = new URLSearchParams();

  if (params?.status) searchParams.append('status', params.status);
  if (params?.clientId !== undefined) searchParams.append('clientId', String(params.clientId));
  if (params?.clientName) searchParams.append('clientName', params.clientName);
  if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));

  const query = searchParams.toString();
  const endpoint = `/api/tasks${query ? `?${query}` : ''}`;

  const response = await apiFetch<ApiResponse<TasksData>>(endpoint);
  return response.data;
}

/**
 * Fetch today's productivity metrics.
 */
export async function getTodayMetrics(): Promise<TodayMetrics> {
  const response = await apiFetch<ApiResponse<TodayMetrics>>('/api/tasks/metrics');
  return response.data;
}

// ============================================================================
// Energy API
// ============================================================================

export interface GetEnergyParams {
  days?: number;
}

/**
 * Fetch energy logs from WorkOS.
 * @param params.days - Number of days to retrieve (1-90, default 7)
 */
export async function getEnergy(params?: GetEnergyParams): Promise<EnergyData> {
  const days = params?.days ?? 7;
  const response = await apiFetch<ApiResponse<EnergyData>>(`/api/energy?days=${days}`);
  return response.data;
}

// ============================================================================
// Health API
// ============================================================================

export interface GetHealthParams {
  days?: number;
}

/**
 * Fetch readiness scores from Oura.
 * @param params.days - Number of days to retrieve (1-90, default 7)
 */
export async function getReadiness(params?: GetHealthParams): Promise<HealthData> {
  const days = params?.days ?? 7;
  const response = await apiFetch<ApiResponse<HealthData>>(`/api/health/readiness?days=${days}`);
  return response.data;
}

// ============================================================================
// Correlations API
// ============================================================================

export interface GetCorrelationsParams {
  days?: number;
}

/**
 * Fetch productivity-health correlations.
 * @param params.days - Number of days to analyze (1-90, default 7)
 */
export async function getCorrelations(params?: GetCorrelationsParams): Promise<CorrelationData> {
  const days = params?.days ?? 7;
  const response = await apiFetch<ApiResponse<CorrelationData>>(`/api/correlations?days=${days}`);
  return response.data;
}

// ============================================================================
// Health Check
// ============================================================================

export interface HealthCheckResponse {
  status: string;
  service: string;
}

/**
 * Check if the backend API is healthy.
 */
export async function checkHealth(): Promise<HealthCheckResponse> {
  return await apiFetch<HealthCheckResponse>('/health');
}

// ============================================================================
// Export all API methods as a single client object
// ============================================================================

export const apiClient = {
  tasks: {
    getTasks,
    getTodayMetrics,
  },
  energy: {
    getEnergy,
  },
  health: {
    getReadiness,
  },
  correlations: {
    getCorrelations,
  },
  checkHealth,
};

export default apiClient;
