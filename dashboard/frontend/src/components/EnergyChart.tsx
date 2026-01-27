import React, { useState, useEffect } from 'react';
import { getEnergy } from '../api/client';
import type { EnergyData, EnergyLog } from '../types';

interface EnergyChartProps {
  refreshInterval?: number; // Optional auto-refresh in milliseconds
}

const EnergyChart: React.FC<EnergyChartProps> = ({ refreshInterval }) => {
  const [energyData, setEnergyData] = useState<EnergyLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);

      const data: EnergyData = await getEnergy({ days: 7 });
      setEnergyData(data.energy_logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch energy data');
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

  // Map energy levels to numeric values for charting
  const energyLevelToValue = (level: string): number => {
    switch (level) {
      case 'high':
        return 3;
      case 'medium':
        return 2;
      case 'low':
        return 1;
      default:
        return 0;
    }
  };

  // Get color for energy level
  const getEnergyColor = (level: string): string => {
    switch (level) {
      case 'high':
        return 'var(--color-success)';
      case 'medium':
        return 'var(--color-warning)';
      case 'low':
        return 'var(--color-danger)';
      default:
        return 'var(--color-text-muted)';
    }
  };

  // Render SVG line chart
  const renderChart = () => {
    if (energyData.length === 0) {
      return (
        <div
          style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
            color: 'var(--color-text-muted)',
          }}
        >
          No energy data available for the past 7 days.
        </div>
      );
    }

    const chartWidth = 280;
    const chartHeight = 120;
    const padding = { top: 10, right: 10, bottom: 30, left: 30 };
    const innerWidth = chartWidth - padding.left - padding.right;
    const innerHeight = chartHeight - padding.top - padding.bottom;

    // Sort by date ascending
    const sortedData = [...energyData].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    // Calculate points for line chart
    const points = sortedData.map((log, index) => {
      const x = padding.left + (index / (sortedData.length - 1)) * innerWidth;
      const value = energyLevelToValue(log.level);
      const y = padding.top + innerHeight - (value / 3) * innerHeight;
      return { x, y, log };
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
      <div style={{ marginTop: 'var(--spacing-md)' }}>
        <svg
          width={chartWidth}
          height={chartHeight}
          style={{
            display: 'block',
            margin: '0 auto',
          }}
        >
          {/* Y-axis labels */}
          <text
            x={padding.left - 10}
            y={padding.top + 5}
            textAnchor="end"
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            High
          </text>
          <text
            x={padding.left - 10}
            y={padding.top + innerHeight / 2 + 5}
            textAnchor="end"
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            Med
          </text>
          <text
            x={padding.left - 10}
            y={padding.top + innerHeight + 5}
            textAnchor="end"
            style={{
              fontSize: '10px',
              fill: 'var(--color-text-muted)',
            }}
          >
            Low
          </text>

          {/* Grid lines */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={chartWidth - padding.right}
            y2={padding.top}
            stroke="var(--color-border)"
            strokeWidth="1"
            opacity="0.3"
          />
          <line
            x1={padding.left}
            y1={padding.top + innerHeight / 2}
            x2={chartWidth - padding.right}
            y2={padding.top + innerHeight / 2}
            stroke="var(--color-border)"
            strokeWidth="1"
            opacity="0.3"
          />
          <line
            x1={padding.left}
            y1={padding.top + innerHeight}
            x2={chartWidth - padding.right}
            y2={padding.top + innerHeight}
            stroke="var(--color-border)"
            strokeWidth="1"
            opacity="0.3"
          />

          {/* Line chart */}
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
              r="4"
              fill={getEnergyColor(point.log.level)}
              stroke="var(--color-bg-primary)"
              strokeWidth="2"
            />
          ))}

          {/* X-axis labels (dates) */}
          {points.map((point, index) => {
            // Show labels for first, middle, and last points
            if (
              index === 0 ||
              index === Math.floor(points.length / 2) ||
              index === points.length - 1
            ) {
              const date = new Date(point.log.date);
              const label = date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
              });
              return (
                <text
                  key={index}
                  x={point.x}
                  y={chartHeight - 10}
                  textAnchor="middle"
                  style={{
                    fontSize: '10px',
                    fill: 'var(--color-text-muted)',
                  }}
                >
                  {label}
                </text>
              );
            }
            return null;
          })}
        </svg>
      </div>
    );
  };

  // Calculate current energy level (latest log)
  const currentEnergy = energyData.length > 0 ? energyData[energyData.length - 1] : null;

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Energy Levels</h3>
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
          <h3 className="card-title">Energy Levels</h3>
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
        <h3 className="card-title">Energy Levels</h3>
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
        {/* Current Energy Level */}
        {currentEnergy && (
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
              Current Level
            </div>
            <div
              style={{
                fontSize: '1.5rem',
                fontWeight: '700',
                color: getEnergyColor(currentEnergy.level),
                textTransform: 'capitalize',
              }}
            >
              {currentEnergy.level}
            </div>
            {currentEnergy.note && (
              <div
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                  marginTop: 'var(--spacing-xs)',
                  fontStyle: 'italic',
                }}
              >
                "{currentEnergy.note}"
              </div>
            )}
          </div>
        )}

        {/* Chart */}
        {renderChart()}

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
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-success)',
              }}
            />
            <span style={{ color: 'var(--color-text-muted)' }}>High</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-xs)' }}>
            <div
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-warning)',
              }}
            />
            <span style={{ color: 'var(--color-text-muted)' }}>Medium</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-xs)' }}>
            <div
              style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-danger)',
              }}
            />
            <span style={{ color: 'var(--color-text-muted)' }}>Low</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnergyChart;
