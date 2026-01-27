/**
 * TypeScript type definitions for Thanos Dashboard API.
 *
 * These types match the API response structures from the FastAPI backend.
 * Backend endpoints:
 * - GET /api/tasks
 * - GET /api/tasks/metrics
 * - GET /api/energy?days=7
 * - GET /api/health/readiness?days=7
 * - GET /api/correlations?days=7
 */

// ============================================================================
// API Response Wrappers
// ============================================================================

export interface ApiResponse<T> {
  success: boolean;
  data: T;
}

// ============================================================================
// Task Types
// ============================================================================

export interface Task {
  id: string;
  title: string;
  status: 'active' | 'queued' | 'backlog' | 'done';
  points?: number;
  clientId?: number;
  clientName?: string;
  createdAt?: string;
  completedAt?: string;
  valueTier?: string;
  drainType?: string;
  cognitiveLoad?: 'high' | 'medium' | 'low';
}

export interface TasksData {
  tasks: Task[];
  count: number;
  filters: {
    status?: string;
    clientId?: number;
    clientName?: string;
    limit?: number;
  };
}

export interface TodayMetrics {
  points_earned: number;
  daily_target: number;
  pace_status: string;
  streak_days: number;
  clients_touched: string[];
  tasks_completed: number;
  tasks_active: number;
}

// ============================================================================
// Energy Types
// ============================================================================

export interface EnergyLog {
  id?: string;
  date: string;
  level: 'high' | 'medium' | 'low';
  note?: string;
  readiness_score?: number;
  hrv?: number;
  sleep_score?: number;
  timestamp?: string;
}

export interface EnergyData {
  energy_logs: EnergyLog[];
  count: number;
  filters: {
    days: number;
  };
}

// ============================================================================
// Health Types
// ============================================================================

export interface ReadinessData {
  id?: string;
  date: string;
  score: number;
  temperature_deviation?: number;
  temperature_trend_deviation?: number;
  contributors?: {
    activity_balance?: number;
    body_temperature?: number;
    hrv_balance?: number;
    previous_day_activity?: number;
    previous_night?: number;
    recovery_index?: number;
    resting_heart_rate?: number;
    sleep_balance?: number;
  };
}

export interface HealthData {
  readiness: ReadinessData[];
  count: number;
  filters: {
    days: number;
  };
}

// ============================================================================
// Correlation Types
// ============================================================================

export interface DailyAggregate {
  date: string;
  tasks_completed: number;
  points_earned: number;
  avg_energy_level?: number;
  readiness_score?: number;
}

export interface CorrelationStats {
  tasks_energy_correlation?: number;
  tasks_readiness_correlation?: number;
  points_energy_correlation?: number;
  points_readiness_correlation?: number;
}

export interface CorrelationData {
  daily_data: DailyAggregate[];
  stats: CorrelationStats;
  days_analyzed: number;
}

// ============================================================================
// API Error Type
// ============================================================================

export interface ApiError {
  detail: string;
  status?: number;
}
