/**
 * FLIP v3.0 — Advisories Page
 */
import { useTranslation } from 'react-i18next';
import { useStore, selectActiveFarm } from '../store';

export function AdvisoriesPage() {
  const { t } = useTranslation('common');
  const activeFarm = useStore(selectActiveFarm);
  const advisories = useStore((s) => s.advisories);
  const markRead = useStore((s) => s.markRead);

  const STATUS_ORDER: Record<string, number> = {
    ACTIVE: 1,
    ACTIONED: 2,
    ACKNOWLEDGED: 3,
    VERIFIED: 4,
    EXPIRED: 5,
    DISMISSED: 6,
  };
  const sorted = [...advisories].sort(
    (a, b) => (STATUS_ORDER[a.status] ?? 5) - (STATUS_ORDER[b.status] ?? 5),
  );

  return (
    <div style={{ padding: '2rem' }}>
      <div className="page-header" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 className="page-title">{t('nav.advisories')}</h1>
          <p className="page-subtitle">
            {activeFarm ? `Farm: ${activeFarm.name}` : 'Select a farm to view advisories'}
          </p>
        </div>
        <span style={{
          fontSize: '0.875rem',
          color: 'var(--color-text-muted)',
          alignSelf: 'center',
        }}>
          {advisories.filter(a => a.status === 'ACTIVE').length} active
        </span>
      </div>

      {sorted.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">✅</span>
          <p>No advisories — your crops look healthy!</p>
        </div>
      ) : (
        <ul className="advisory-list">
          {sorted.map((advisory) => (
            <li
              key={advisory.id}
              className={`advisory-item severity-${advisory.status.toLowerCase()}`}
              style={{ opacity: advisory.status === 'ACKNOWLEDGED' ? 0.6 : 1 }}
            >
              <div className="advisory-header">
                <span className="advisory-type">{advisory.prediction_set?.[0] || 'GENERAL ADVISORY'}</span>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span className={`severity-badge ${advisory.status.toLowerCase()}`}>
                    {advisory.status}
                  </span>
                  {advisory.status === 'ACKNOWLEDGED' ? (
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-success)' }}>✓ Acknowledged</span>
                  ) : (
                    <button
                      style={{
                        background: 'var(--color-primary-glow)',
                        border: '1px solid var(--color-primary)',
                        color: 'var(--color-primary)',
                        padding: '2px 10px',
                        borderRadius: '9999px',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                        fontWeight: 600,
                      }}
                      onClick={() => markRead(advisory.id)}
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
              <h3 className="advisory-title">{advisory.now_text}</h3>
              <p className="advisory-body">{advisory.next_text || advisory.why_text}</p>
              {advisory.why_text && advisory.next_text && (
                <p style={{ marginTop: '0.5rem', fontSize: '0.8125rem', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                  Rationale: {advisory.why_text}
                </p>
              )}
              <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                Coverage: {Math.round((advisory.coverage_target ?? 0.95) * 100)}% · Model: {advisory.model_version}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
