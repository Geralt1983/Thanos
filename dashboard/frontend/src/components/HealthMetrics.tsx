import React, { useState, useEffect } from 'react';
import { getReadiness } from '../api/client';
import type { HealthData, ReadinessData } from '../types';

interface HealthMetricsProps {
  refreshInterval?: number; // Optional auto-refresh in milliseconds
}

const HealthMetrics: React.FC<HealthMetricsProps> = ({ refreshInterval }) => {
  const [readinessData, setReadinessData] = useState<ReadinessData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);

      const data: HealthData = await getReadiness({ days: 7 });
      setReadinessData(data.readiness);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health data');
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

  // Get readiness score color based on value
  const getReadinessColor = (score: number): string => {
    if (score >= 85) return 'var(--color-success)';
    if (score >= 70) return 'var(--color-warning)';
    return 'var(--color-danger)';
  };

  // Render mini trend sparkline
  const renderSparkline = () => {
    if (readinessData.length === 0) return null;

    const width = 280;
    const height = 40;
    const padding = 2;

    // Sort by date ascending
    const sortedData = [...readinessData].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    // Calculate points for sparkline
    const maxScore = 100;
    const minScore = 0;
    const range = maxScore - minScore;

    const points = sortedData.map((data, index) => {
      const x = padding + (index / (sortedData.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((data.score - minScore) / range) * (height - 2 * padding);
      return { x, y, score: data.score };
    });

    // Generate SVG path
    const pathData = points
      .map((point, index) => {
        if (index === 0) {
          return `M ${point.x} ${point.y}`;
        }
        return `L ${point.x} ${point.y}`;
      })
      .join(' ');

    return (
      <svg
        width={width}
        height={height}
        style={{
          display: 'block',
          margin: '0 auto',
        }}
      >
        {/* Area fill */}
        <path
          d={`${pathData} L ${points[points.length - 1].x} ${height} L ${points[0].x} ${height} Z`}
          fill="var(--color-accent-primary)"
          opacity="0.1"
        />

        {/* Line */}
        <path
          d={pathData}
          fill="none"
          stroke="var(--color-accent-primary)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Data points */}
        {points.map((point, index) => (
          <circle
            key={index}
            cx={point.x}
            cy={point.y}
            r="3"
            fill={getReadinessColor(point.score)}
            stroke="var(--color-bg-primary)"
            strokeWidth="1.5"
          />
        ))}
      </svg>
    );
  };

  // Calculate current readiness (latest data)
  const currentReadiness = readinessData.length > 0 ? readinessData[readinessData.length - 1] : null;

  // Calculate average readiness over period
  const avgReadiness =
    readinessData.length > 0
      ? Math.round(readinessData.reduce((sum, data) => sum + data.score, 0) / readinessData.length)
      : 0;

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Health Metrics</h3>
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
          <h3 className="card-title">Health Metrics</h3>
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
        <h3 className="card-title">Health Metrics</h3>
        <span
          style={{
            fontSize: '0.875rem',
            color: 'var(--color-text-muted)',
          }}
        >
          7-day trend
        </span>
      </div>
      <div className="card-content">
        {currentReadiness ? (
          <>
            {/* Current Readiness Score */}
            <div style={{ marginBottom: 'var(--spacing-lg)' }}>
              <div
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  marginBottom: 'var(--spacing-xs)',
                }}
              >
                Readiness Score
              </div>
              <div
                style={{
                  fontSize: '2.5rem',
                  fontWeight: '700',
                  color: getReadinessColor(currentReadiness.score),
                  lineHeight: '1',
                }}
              >
                {currentReadiness.score}
              </div>
              <div
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                  marginTop: 'var(--spacing-xs)',
                }}
              >
                {new Date(currentReadiness.date).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </div>
            </div>

            {/* Trend Sparkline */}
            {renderSparkline()}

            {/* Stats Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: 'var(--spacing-md)',
                marginTop: 'var(--spacing-lg)',
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
                  7-Day Avg
                </div>
                <div
                  style={{
                    fontSize: '1.5rem',
                    fontWeight: '700',
                    color: getReadinessColor(avgReadiness),
                  }}
                >
                  {avgReadiness}
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
                  Sleep Balance
                </div>
                <div
                  style={{
                    fontSize: '1.5rem',
                    fontWeight: '700',
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {currentReadiness.contributors?.sleep_balance
                    ? Math.round(currentReadiness.contributors.sleep_balance)
                    : '—'}
                </div>
              </div>
            </div>

            {/* Contributors */}
            {currentReadiness.contributors && (
              <div
                style={{
                  marginTop: 'var(--spacing-lg)',
                  padding: 'var(--spacing-md)',
                  backgroundColor: 'var(--color-bg-secondary)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div
                  style={{
                    fontSize: '0.75rem',
                    color: 'var(--color-text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 'var(--spacing-sm)',
                  }}
                >
                  Top Contributors
                </div>
                <div
                  style={{
                    display: 'grid',
                    gap: 'var(--spacing-xs)',
                    fontSize: '0.875rem',
                  }}
                >
                  {currentReadiness.contributors.previous_night !== undefined && (
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      <span>Previous Night</span>
                      <span style={{ fontWeight: '500' }}>
                        {Math.round(currentReadiness.contributors.previous_night)}
                      </span>
                    </div>
                  )}
                  {currentReadiness.contributors.hrv_balance !== undefined && (
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      <span>HRV Balance</span>
                      <span style={{ fontWeight: '500' }}>
                        {Math.round(currentReadiness.contributors.hrv_balance)}
                      </span>
                    </div>
                  )}
                  {currentReadiness.contributors.recovery_index !== undefined && (
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      <span>Recovery Index</span>
                      <span style={{ fontWeight: '500' }}>
                        {Math.round(currentReadiness.contributors.recovery_index)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        ) : (
          <div
            style={{
              textAlign: 'center',
              padding: 'var(--spacing-xl)',
              color: 'var(--color-text-muted)',
            }}
          >
            No health data available for the past 7 days.
          </div>
        )}
      </div>
    </div>
  );
};

export default HealthMetrics;
