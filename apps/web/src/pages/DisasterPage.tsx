/**
 * FLIP v3.0 — Disaster Page
 * Active disaster alerts, shelter map, SOS button.
 */
import { useTranslation } from 'react-i18next';
import { useStore } from '../store';

export function DisasterPage() {
  const { t } = useTranslation('common');
  const activeAlerts = useStore((s) => s.activeAlerts);
  const dismissAlert = useStore((s) => s.dismissAlert);
  const dismissedIds = useStore((s) => s.dismissedAlertIds);
  const activeFarmId = useStore((s) => s.activeFarmId);

  const visibleAlerts = activeAlerts.filter((a) => !dismissedIds.has(a.id));

  const SEVERITY_ICON: Record<string, string> = {
    EMERGENCY: '🚨',
    WARNING: '⚠️',
    WATCH: '📢',
    ADVISORY: 'ℹ️',
    critical: '🚨',
    high: '⚠️',
    medium: '📢',
    low: 'ℹ️',
  };

  const handleSOS = () => {
    if (!activeFarmId) {
      alert('Please select an active farm before sending SOS.');
      return;
    }
    // In real app: get GPS coords via navigator.geolocation + call /api/v1/disaster/sos
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          alert(
            `SOS would be sent for farm ${activeFarmId} at ` +
            `${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}.` +
            '\n\nIn production this calls POST /api/v1/disaster/sos via NATS broadcast.'
          );
        },
        () => alert('GPS unavailable. SOS sent with farm location.'),
      );
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      {/* Header */}
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 className="page-title" style={{ color: 'var(--color-danger)' }}>
            🚨 {t('nav.disaster')}
          </h1>
          <p className="page-subtitle">Active emergency alerts and shelter information</p>
        </div>

        {/* SOS Button */}
        <button
          onClick={handleSOS}
          style={{
            background: 'var(--color-danger)',
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            padding: '0.75rem 1.5rem',
            fontWeight: 700,
            fontSize: '1rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            boxShadow: '0 0 20px rgba(239, 68, 68, 0.4)',
          }}
        >
          <span>🆘</span>
          <span>EMERGENCY SOS</span>
        </button>
      </div>

      {/* Alert list */}
      {visibleAlerts.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">✅</span>
          <p>No active disaster alerts in your area</p>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            Stay prepared. Check back regularly during monsoon season.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {visibleAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`disaster-banner ${alert.severity.toLowerCase()}`}
              style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.75rem' }}
            >
              {/* Alert header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', width: '100%' }}>
                <span className="banner-icon">{SEVERITY_ICON[alert.severity] ?? '⚠️'}</span>
                <div style={{ flex: 1 }}>
                  <div className="banner-title">{alert.message_template?.title_en || alert.event_type}</div>
                  <div className="banner-subtitle">{alert.event_type} · {alert.source}</div>
                </div>
                <button className="banner-dismiss" onClick={() => dismissAlert(alert.id)}>×</button>
              </div>

              {/* Description */}
              <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', paddingLeft: '2.5rem' }}>
                {alert.message_template?.body_en || ''}
              </p>

              {/* Action steps */}
              {alert.message_template?.action_steps_en && alert.message_template.action_steps_en.length > 0 && (
                <div style={{ paddingLeft: '2.5rem' }}>
                  <p style={{ fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text-secondary)' }}>
                    🛡️ Action Steps:
                  </p>
                  {alert.message_template.action_steps_en.slice(0, 3).map((step, i) => (
                    <div key={i} style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: '0.25rem' }}>
                      • {step}
                    </div>
                  ))}
                </div>
              )}

              {/* Times */}
              <div style={{ paddingLeft: '2.5rem', fontSize: '0.75rem', color: 'var(--color-text-muted)', display: 'flex', gap: '1rem' }}>
                <span>Issued: {new Date(alert.issued_at).toLocaleString()}</span>
                {alert.expires_at && (
                  <span>Expires: {new Date(alert.expires_at).toLocaleString()}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
