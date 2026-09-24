/**
 * FLIP v3.0 — Dashboard Page
 * Main farmer dashboard: farm overview, live sensors, advisories, weather.
 */

import { useTranslation } from 'react-i18next';
import { useStore, selectActiveFarm, selectUnreadAdvisories, selectCriticalAlerts } from '../store';
import { useLiveSensors } from '../hooks/useLiveSensors';
import { DisasterBanner } from '../components/DisasterBanner';
import { SensorLiveCard } from '../components/SensorLiveCard';
import { FarmMap } from '../components/FarmMap';

export function DashboardPage() {
  const { t } = useTranslation('common');
  const activeFarm = useStore(selectActiveFarm);
  const unreadAdvisories = useStore(selectUnreadAdvisories);
  const criticalAlerts = useStore(selectCriticalAlerts);
  const liveReadings = useStore((s) => s.liveReadings);

  // Connect live sensor stream
  useLiveSensors({ farmId: activeFarm?.id ?? null });

  const sensorMetrics = ['temperature', 'humidity', 'soil_moisture', 'ph', 'nitrogen'];

  return (
    <div className="dashboard-page">
      {/* Disaster Alert Banner */}
      {criticalAlerts.map((alert) => (
        <DisasterBanner
          key={alert.id}
          type={alert.event_type}
          severity={alert.severity}
          title={alert.message_template?.title_en || alert.event_type}
          titleHi={alert.message_template?.title_hi}
          message={alert.message_template?.body_en || ''}
          messageHi={alert.message_template?.body_hi}
        />
      ))}

      {/* Page Header */}
      <header className="page-header">
        <div>
          <h1 className="page-title">{t('nav.dashboard')}</h1>
          {activeFarm && (
            <p className="page-subtitle">
              {activeFarm.name} {activeFarm.area_acres ? `· ${activeFarm.area_acres} Acres` : ''} {activeFarm.soil_type ? `· ${activeFarm.soil_type}` : ''}
            </p>
          )}
        </div>
        {unreadAdvisories.length > 0 && (
          <div className="advisory-badge">
            <span className="badge-count">{unreadAdvisories.length}</span>
            <span className="badge-label">{t('nav.advisories')}</span>
          </div>
        )}
      </header>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Sensor Cards Row */}
        <section className="sensor-grid">
          {sensorMetrics.map((metric) => {
            const sensorId = `${activeFarm?.id}-${metric}`;
            return (
              <SensorLiveCard
                key={metric}
                reading={liveReadings[sensorId]}
                metric={metric}
              />
            );
          })}
        </section>

        {/* Map Section */}
        <section className="map-section">
          <FarmMap farmId={activeFarm?.id} />
        </section>

        {/* Advisory Panel */}
        <section className="advisory-panel">
          <h2 className="section-title">{t('nav.advisories')}</h2>
          {unreadAdvisories.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">✅</span>
              <p>No pending advisories</p>
            </div>
          ) : (
            <ul className="advisory-list">
              {unreadAdvisories.slice(0, 5).map((advisory) => (
                <li key={advisory.id} className={`advisory-item severity-${advisory.status}`}>
                  <div className="advisory-header">
                    <span className="advisory-type">{advisory.prediction_set?.[0] || 'ADVISORY'}</span>
                    <span className={`severity-badge ${advisory.status.toLowerCase()}`}>
                      {advisory.status}
                    </span>
                  </div>
                  <p className="advisory-title">{advisory.now_text}</p>
                  <p className="advisory-body">{advisory.next_text ? advisory.next_text.slice(0, 120) : advisory.why_text.slice(0, 120)}…</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
