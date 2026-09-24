/**
 * FLIP v3.0 — Updated SensorLiveCard Component
 * Live sensor data card with real value rendering, trend, and quality indicator.
 */

import { useTranslation } from 'react-i18next';
import type { SensorReading } from '@flip/shared-types';

interface SensorLiveCardProps {
  reading?: SensorReading;
  metric: string;
}

const METRIC_CONFIG: Record<string, { icon: string; unit: string; decimals: number; normalRange?: [number, number] }> = {
  temperature:   { icon: '🌡️', unit: '°C',  decimals: 1, normalRange: [20, 35] },
  humidity:      { icon: '💧', unit: '%',   decimals: 1, normalRange: [40, 80] },
  soil_moisture: { icon: '🌱', unit: '%',   decimals: 1, normalRange: [30, 70] },
  ph:            { icon: '⚗️', unit: 'pH',  decimals: 2, normalRange: [5.5, 7.5] },
  nitrogen:      { icon: '🧪', unit: 'ppm', decimals: 0, normalRange: [20, 60] },
  phosphorus:    { icon: '🔬', unit: 'ppm', decimals: 0, normalRange: [10, 40] },
  potassium:     { icon: '⚡', unit: 'ppm', decimals: 0, normalRange: [100, 250] },
  rainfall:      { icon: '🌧️', unit: 'mm',  decimals: 1 },
  light:         { icon: '☀️', unit: 'lux', decimals: 0 },
  battery:       { icon: '🔋', unit: '%',   decimals: 0, normalRange: [20, 100] },
};

function getValueColor(value: number, normalRange?: [number, number]): string {
  if (!normalRange) return 'var(--color-text-primary)';
  const [min, max] = normalRange;
  if (value < min * 0.8 || value > max * 1.2) return 'var(--color-danger)';
  if (value < min || value > max) return 'var(--color-warning)';
  return 'var(--color-success)';
}

export function SensorLiveCard({ reading, metric }: SensorLiveCardProps) {
  const { t } = useTranslation('common');
  const config = METRIC_CONFIG[metric] ?? { icon: '📊', unit: '', decimals: 1 };

  const isLive = reading !== undefined;
  const displayValue = reading ? reading.value.toFixed(config.decimals) : '—';
  const valueColor = reading ? getValueColor(reading.value, config.normalRange) : 'var(--color-text-muted)';

  return (
    <div className={`sensor-card ${isLive ? 'live' : ''}`} title={t(`sensor.${metric}`, metric)}>
      {/* Live indicator */}
      {isLive && (
        <div style={{
          position: 'absolute',
          top: '0.75rem',
          right: '0.75rem',
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: 'var(--color-success)',
          animation: 'pulse 2s infinite',
        }} />
      )}

      <div className="sensor-icon">{config.icon}</div>
      <div className="sensor-metric">{t(`sensor.${metric}`, { defaultValue: metric.replace(/_/g, ' ') })}</div>
      <div className="sensor-value" style={{ color: valueColor }}>
        {displayValue}
        <span className="sensor-unit" style={{ fontSize: '0.875rem', marginLeft: '4px', color: 'var(--color-text-secondary)' }}>
          {config.unit}
        </span>
      </div>

      {reading && (
        <>
          {/* Quality bar */}
          <div style={{
            marginTop: '0.75rem',
            height: 3,
            background: 'var(--color-bg-base)',
            borderRadius: 2,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${reading.quality_flag === 'VALID' ? 100 : 70}%`,
              background: reading.quality_flag === 'VALID' ? 'var(--color-success)' : 'var(--color-warning)',
              borderRadius: 2,
              transition: 'width 0.5s ease',
            }} />
          </div>
          <div className="sensor-quality">
            Quality: {reading.quality_flag}
          </div>

          {/* Timestamp */}
          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            {t('sensor.last_seen', {
              time: new Date(reading.time).toLocaleTimeString(),
            })}
          </div>
        </>
      )}

      {!isLive && (
        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
          Waiting for data...
        </div>
      )}
    </div>
  );
}
