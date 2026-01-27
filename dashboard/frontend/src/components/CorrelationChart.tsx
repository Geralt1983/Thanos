import React, { useState, useEffect } from 'react';
import { getCorrelations } from '../api/client';
import type { CorrelationData, DailyAggregate } from '../types';

interface CorrelationChartProps {
  refreshInterval?: number; // Optional auto-refresh in milliseconds
}

const CorrelationChart: React.FC<CorrelationChartProps> = ({ refreshInterval }) => {
  const [correlationData, setCorrelationData] = useState<CorrelationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);

      const data: CorrelationData = await getCorrelations({ days: 7 });
      setCorrelationData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch correlation data');
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

  // Get color based on correlation strength
  const getCorrelationColor = (correlation?: number): string => {
    if (correlation === undefined) return 'var(--color-text-muted)';
    const abs = Math.abs(correlation);
    if (abs >= 0.7) return 'var(--color-success)';
    if (abs >= 0.4) return 'var(--color-warning)';
    return 'var(--color-text-muted)';
  };

  // Format correlation value
  const formatCorrelation = (correlation?: number): string => {
    if (correlation === undefined) return '—';
    return correlation > 0 ? `+${correlation.toFixed(2)}` : correlation.toFixed(2);
  };

  // Render scatter plot showing energy vs productivity
  const renderScatterPlot = () => {
    if (!correlationData || correlationData.daily_data.length === 0) {
      return (
        <div
          style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
            color: 'var(--color-text-muted)',
          }}
        >
          No correlation data available for the past 7 days.
        </div>
      );
    }

    const chartWidth = 280;
    const chartHeight = 140;
    const padding = { top: 20, right: 20, bottom: 30, left: 40 };
    const innerWidth = chartWidth - padding.left - padding.right;
    const innerHeight = chartHeight - padding.top - padding.bottom;

    // Filter data to only include entries with both energy and productivity data
    const validData = correlationData.daily_data.filter(
      (d) => d.avg_energy_level !== undefined && d.points_earned !== undefined
    );

    if (validData.length === 0) {
      return (
        <div
          style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
            color: 'var(--color-text-muted)',
          }}
        >
          Not enough data to show correlations.
        </div>
      );
    }

    // Calculate scales
    const energyLevels = validData.map((d) => d.avg_energy_level!);
    const points = validData.map((d) => d.points_earned!);

    const minEnergy = Math.min(...energyLevels);
    const maxEnergy = Math.max(...energyLevels);
    const minPoints = Math.min(...points);
    const maxPoints = Math.max(...points);

    // Add padding to scales
    const energyRange = maxEnergy - minEnergy || 1;
    const pointsRange = maxPoints - minPoints || 1;

    // Calculate point positions
    const plotPoints = validData.map((d) => {
      const x =
        padding.left +
        ((d.avg_energy_level! - minEnergy) / energyRange) * innerWidth;
      const y =
        padding.top +
        innerHeight -
        ((d.points_earned! - minPoints) / pointsRange) * innerHeight;
      return { x, y, data: d };
    });

    return (
      <div style={{ marginTop: 'var(--spacing-md)' }}>
        <svg
          width={chartWidth}
          height={chartHeight}
          style={{
            display: 'block',
            margin: '0 auto',
          }}
        >
          {/* Y-axis label (Productivity) */}
          <text
            x={5}
            y={padding.top - 5}
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            Points
          </text>

          {/* X-axis label (Energy) */}
          <text
            x={chartWidth - 35}
            y={chartHeight - 5}
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            Energy
          </text>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
            <React.Fragment key={i}>
              {/* Horizontal grid lines */}
              <line
                x1={padding.left}
                y1={padding.top + innerHeight * ratio}
                x2={chartWidth - padding.right}
                y2={padding.top + innerHeight * ratio}
                stroke="var(--color-border)"
                strokeWidth="1"
                opacity="0.2"
              />
              {/* Vertical grid lines */}
              <line
                x1={padding.left + innerWidth * ratio}
                y1={padding.top}
                x2={padding.left + innerWidth * ratio}
                y2={chartHeight - padding.bottom}
                stroke="var(--color-border)"
                strokeWidth="1"
                opacity="0.2"
              />
            </React.Fragment>
          ))}

          {/* Axes */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={chartHeight - padding.bottom}
            stroke="var(--color-border)"
            strokeWidth="2"
          />
          <line
            x1={padding.left}
            y1={chartHeight - padding.bottom}
            x2={chartWidth - padding.right}
            y2={chartHeight - padding.bottom}
            stroke="var(--color-border)"
            strokeWidth="2"
          />

          {/* Data points */}
          {plotPoints.map((point, index) => (
            <circle
              key={index}
              cx={point.x}
              cy={point.y}
              r="5"
              fill="var(--color-accent-primary)"
              opacity="0.7"
              stroke="var(--color-bg-primary)"
              strokeWidth="2"
            />
          ))}

          {/* Y-axis tick labels */}
          <text
            x={padding.left - 5}
            y={padding.top + 5}
            textAnchor="end"
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            {maxPoints}
          </text>
          <text
            x={padding.left - 5}
            y={chartHeight - padding.bottom + 5}
            textAnchor="end"
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            {minPoints}
          </text>

          {/* X-axis tick labels */}
          <text
            x={padding.left}
            y={chartHeight - 10}
            textAnchor="middle"
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            {minEnergy.toFixed(1)}
          </text>
          <text
            x={chartWidth - padding.right}
            y={chartHeight - 10}
            textAnchor="middle"
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            {maxEnergy.toFixed(1)}
          </text>
        </svg>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Correlations</h3>
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
          <h3 className="card-title">Correlations</h3>
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
        <h3 className="card-title">Correlations</h3>
        <span
          style={{
            fontSize: '0.875rem',
            color: 'var(--color-text-muted)',
          }}
        >
          Energy vs Productivity
        </span>
      </div>
      <div className="card-content">
        {correlationData && (
          <>
            {/* Correlation Stats */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr',
                gap: 'var(--spacing-sm)',
                marginBottom: 'var(--spacing-lg)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span
                  style={{
                    fontSize: '0.875rem',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  Points ↔ Energy
                </span>
                <span
                  style={{
                    fontSize: '1rem',
                    fontWeight: '700',
                    color: getCorrelationColor(correlationData.stats.points_energy_correlation),
                  }}
                >
                  {formatCorrelation(correlationData.stats.points_energy_correlation)}
                </span>
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span
                  style={{
                    fontSize: '0.875rem',
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  Points ↔ Readiness
                </span>
                <span
                  style={{
                    fontSize: '1rem',
                    fontWeight: '700',
                    color: getCorrelationColor(correlationData.stats.points_readiness_correlation),
                  }}
                >
                  {formatCorrelation(correlationData.stats.points_readiness_correlation)}
                </span>
              </div>
            </div>

            {/* Scatter Plot */}
            {renderScatterPlot()}

            {/* Legend */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                gap: 'var(--spacing-md)',
                marginTop: 'var(--spacing-md)',
                fontSize: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-xs)' }}>
                <div
                  style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--color-accent-primary)',
                    opacity: '0.7',
                  }}
                />
                <span style={{ color: 'var(--color-text-muted)' }}>
                  Daily data ({correlationData.days_analyzed} days)
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default CorrelationChart;
