/**
 * FLIP v3.0 — Farms Page (stub)
 */
import { useTranslation } from 'react-i18next';
import { useStore } from '../store';

export function FarmsPage() {
  const { t } = useTranslation('common');
  const farms = useStore((s) => s.farms);
  const setActiveFarm = useStore((s) => s.setActiveFarm);
  const activeFarmId = useStore((s) => s.activeFarmId);

  return (
    <div style={{ padding: '2rem' }}>
      <h1 className="page-title">{t('nav.farms')}</h1>
      <p className="page-subtitle" style={{ marginBottom: '2rem' }}>
        Manage your farm profiles and select an active farm
      </p>
      {farms.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">🌾</span>
          <p>{t('farm.no_farms')}</p>
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>
            Your farms will appear here once synced from the server.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {farms.map((farm) => (
            <div
              key={farm.id}
              className="sensor-card"
              style={{
                cursor: 'pointer',
                borderColor: activeFarmId === farm.id ? 'var(--color-primary)' : undefined,
              }}
              onClick={() => setActiveFarm(farm.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && setActiveFarm(farm.id)}
            >
              <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>🌾</div>
              <h3 style={{ fontWeight: 600, marginBottom: '0.5rem' }}>{farm.name}</h3>
              <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                {farm.area_acres ? `${farm.area_acres} Acres` : 'Standard Farm Plot'} {farm.soil_type ? `· ${farm.soil_type}` : ''}
              </p>
              {farm.irrigation_source && (
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
                  💧 Irrigation: {farm.irrigation_source}
                </p>
              )}
              {activeFarmId === farm.id && (
                <span style={{
                  display: 'inline-block',
                  marginTop: '0.75rem',
                  fontSize: '0.75rem',
                  background: 'var(--color-primary-glow)',
                  color: 'var(--color-primary)',
                  padding: '2px 10px',
                  borderRadius: '9999px',
                  fontWeight: 600,
                }}>
                  ✓ Active
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
