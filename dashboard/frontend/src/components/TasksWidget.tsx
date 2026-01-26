import React, { useState, useEffect } from 'react';
import { getTasks, getTodayMetrics } from '../api/client';
import type { Task, TodayMetrics } from '../types';

interface TasksWidgetProps {
  refreshInterval?: number; // Optional auto-refresh in milliseconds
}

const TasksWidget: React.FC<TasksWidgetProps> = ({ refreshInterval }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [metrics, setMetrics] = useState<TodayMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);

      // Fetch active tasks and today's metrics in parallel
      const [tasksData, metricsData] = await Promise.all([
        getTasks({ status: 'active', limit: 10 }),
        getTodayMetrics(),
      ]);

      setTasks(tasksData.tasks);
      setMetrics(metricsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Setup auto-refresh if interval provided
    if (refreshInterval) {
      const intervalId = setInterval(fetchData, refreshInterval);
      return () => clearInterval(intervalId);
    }
  }, [refreshInterval]);

  // Calculate progress percentage
  const progressPercent = metrics
    ? Math.min(Math.round((metrics.points_earned / metrics.daily_target) * 100), 100)
    : 0;

  // Determine pace status color
  const getPaceColor = (status: string) => {
    if (status.includes('ahead')) return 'var(--color-success)';
    if (status.includes('behind')) return 'var(--color-danger)';
    return 'var(--color-warning)';
  };

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Today's Tasks</h3>
        </div>
        <div className="card-content">
          <div className="loading">
            <div className="spinner"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Today's Tasks</h3>
        </div>
        <div className="card-content">
          <div className="error">
            <strong>Error:</strong> {error}
          </div>
          <button
            onClick={fetchData}
            style={{
              marginTop: 'var(--spacing-md)',
              padding: 'var(--spacing-sm) var(--spacing-md)',
              backgroundColor: 'var(--color-accent-primary)',
              color: 'var(--color-text-primary)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '500',
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Today's Tasks</h3>
        <span
          style={{
            fontSize: '0.875rem',
            color: 'var(--color-text-muted)',
          }}
        >
          {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </span>
      </div>
      <div className="card-content">
        {/* Daily Progress */}
        {metrics && (
          <div style={{ marginBottom: 'var(--spacing-lg)' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 'var(--spacing-sm)',
              }}
            >
              <span
                style={{
                  fontSize: '1.5rem',
                  fontWeight: '700',
                  color: 'var(--color-accent-gold)',
                }}
              >
                {metrics.points_earned}
              </span>
              <span
                style={{
                  fontSize: '0.875rem',
                  color: 'var(--color-text-muted)',
                }}
              >
                / {metrics.daily_target} pts
              </span>
            </div>

            {/* Progress Bar */}
            <div
              style={{
                width: '100%',
                height: '8px',
                backgroundColor: 'var(--color-bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                overflow: 'hidden',
                marginBottom: 'var(--spacing-sm)',
              }}
            >
              <div
                style={{
                  width: `${progressPercent}%`,
                  height: '100%',
                  backgroundColor: 'var(--color-accent-gold)',
                  transition: 'width 0.3s ease-in-out',
                }}
              />
            </div>

            {/* Pace Status */}
            <div
              style={{
                fontSize: '0.875rem',
                color: getPaceColor(metrics.pace_status),
                fontWeight: '500',
              }}
            >
              {metrics.pace_status}
            </div>
          </div>
        )}

        {/* Task Stats */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: 'var(--spacing-md)',
            marginBottom: 'var(--spacing-lg)',
          }}
        >
          <div>
            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: 'var(--spacing-xs)',
              }}
            >
              Active
            </div>
            <div
              style={{
                fontSize: '1.5rem',
                fontWeight: '700',
                color: 'var(--color-text-primary)',
              }}
            >
              {metrics?.tasks_active || tasks.length}
            </div>
          </div>
          <div>
            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: 'var(--spacing-xs)',
              }}
            >
              Done
            </div>
            <div
              style={{
                fontSize: '1.5rem',
                fontWeight: '700',
                color: 'var(--color-success)',
              }}
            >
              {metrics?.tasks_completed || 0}
            </div>
          </div>
        </div>

        {/* Streak */}
        {metrics && metrics.streak_days > 0 && (
          <div
            style={{
              padding: 'var(--spacing-sm) var(--spacing-md)',
              backgroundColor: 'rgba(139, 124, 200, 0.1)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-accent-primary)',
              marginBottom: 'var(--spacing-md)',
            }}
          >
            <div
              style={{
                fontSize: '0.875rem',
                color: 'var(--color-accent-primary)',
                fontWeight: '500',
              }}
            >
              🔥 {metrics.streak_days} day streak
            </div>
          </div>
        )}

        {/* Task List Preview */}
        {tasks.length > 0 && (
          <div>
            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: 'var(--spacing-sm)',
              }}
            >
              Next up
            </div>
            <ul
              style={{
                listStyle: 'none',
                margin: 0,
                padding: 0,
              }}
            >
              {tasks.slice(0, 3).map((task) => (
                <li
                  key={task.id}
                  style={{
                    fontSize: '0.875rem',
                    color: 'var(--color-text-secondary)',
                    marginBottom: 'var(--spacing-xs)',
                    paddingLeft: 'var(--spacing-md)',
                    position: 'relative',
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      left: '0',
                      color: 'var(--color-accent-primary)',
                    }}
                  >
                    •
                  </span>
                  {task.title}
                  {task.points && (
                    <span
                      style={{
                        marginLeft: 'var(--spacing-xs)',
                        color: 'var(--color-accent-gold)',
                        fontSize: '0.75rem',
                      }}
                    >
                      ({task.points}pts)
                    </span>
                  )}
                </li>
              ))}
            </ul>
            {tasks.length > 3 && (
              <div
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                  marginTop: 'var(--spacing-sm)',
                }}
              >
                +{tasks.length - 3} more
              </div>
            )}
          </div>
        )}

        {tasks.length === 0 && (
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--spacing-lg)',
              color: 'var(--color-text-muted)',
            }}
          >
            No active tasks. The universe is balanced.
          </div>
        )}
      </div>
    </div>
  );
};

export default TasksWidget;
