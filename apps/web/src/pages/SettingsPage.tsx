/**
 * FLIP v3.0 — Settings Page
 * Language selection, map style, account info, offline status.
 */
import { useTranslation } from 'react-i18next';
import i18n, { SUPPORTED_LOCALES } from '../i18n';
import { useStore } from '../store';
import { useAuth } from '../hooks/useAuth';

export function SettingsPage() {
  const { t } = useTranslation('common');
  const locale = useStore((s) => s.locale);
  const setLocale = useStore((s) => s.setLocale);
  const mapStyle = useStore((s) => s.mapStyle);
  const setMapStyle = useStore((s) => s.setMapStyle);
  const pendingCount = useStore((s) => s.pendingActions.length);
  const isOnline = useStore((s) => s.isOnline);
  const { user, roles, logout } = useAuth();

  const handleLocaleChange = (newLocale: typeof locale) => {
    setLocale(newLocale);
    void i18n.changeLanguage(newLocale);
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '640px' }}>
      <h1 className="page-title" style={{ marginBottom: '2rem' }}>{t('nav.settings')}</h1>

      {/* Language */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 className="section-title">🌐 Language</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.75rem', marginTop: '1rem' }}>
          {SUPPORTED_LOCALES.map((loc) => (
            <button
              key={loc.code}
              onClick={() => handleLocaleChange(loc.code as typeof locale)}
              style={{
                padding: '0.75rem',
                borderRadius: '0.5rem',
                border: `1px solid ${locale === loc.code ? 'var(--color-primary)' : 'var(--color-border)'}`,
                background: locale === loc.code ? 'var(--color-primary-glow)' : 'var(--color-bg-elevated)',
                color: locale === loc.code ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                fontWeight: locale === loc.code ? 600 : 400,
                textAlign: 'left',
                transition: 'all 150ms ease',
              }}
            >
              <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{loc.nativeName}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>{loc.name}</div>
            </button>
          ))}
        </div>
      </section>

      {/* Map Style */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 className="section-title">🗺️ Map Style</h2>
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
          {(['satellite', 'terrain', 'street'] as const).map((style) => (
            <button
              key={style}
              onClick={() => setMapStyle(style)}
              style={{
                padding: '0.75rem 1.25rem',
                borderRadius: '0.5rem',
                border: `1px solid ${mapStyle === style ? 'var(--color-primary)' : 'var(--color-border)'}`,
                background: mapStyle === style ? 'var(--color-primary-glow)' : 'var(--color-bg-elevated)',
                color: mapStyle === style ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                cursor: 'pointer',
                textTransform: 'capitalize',
                fontWeight: mapStyle === style ? 600 : 400,
                transition: 'all 150ms ease',
              }}
            >
              {style === 'satellite' ? '🛰️' : style === 'terrain' ? '⛰️' : '🏙️'} {style}
            </button>
          ))}
        </div>
      </section>

      {/* Offline Status */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 className="section-title">📡 Connectivity</h2>
        <div style={{
          marginTop: '1rem',
          padding: '1rem 1.25rem',
          borderRadius: '0.5rem',
          background: 'var(--color-bg-elevated)',
          border: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}>
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: isOnline ? 'var(--color-success)' : 'var(--color-danger)',
            animation: 'pulse 2s infinite',
          }} />
          <div>
            <div style={{ fontWeight: 500, fontSize: '0.875rem' }}>
              {isOnline ? 'Online' : 'Offline Mode'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              {pendingCount > 0
                ? `${pendingCount} action(s) pending sync`
                : 'All data synced'}
            </div>
          </div>
        </div>
      </section>

      {/* Account */}
      {user && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 className="section-title">👤 Account</h2>
          <div style={{
            marginTop: '1rem',
            padding: '1.25rem',
            borderRadius: '0.5rem',
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)',
          }}>
            <div style={{ fontWeight: 600 }}>{user.profile.name || user.profile.preferred_username || 'FLIP User'}</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem' }}>{user.profile.email || (user.profile as Record<string, unknown>).phone_number as string || ''}</div>
            {roles && roles.length > 0 && (
              <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {roles.map((role: string) => (
                  <span key={role} style={{
                    fontSize: '0.7rem',
                    background: 'var(--color-bg-glass)',
                    border: '1px solid var(--color-border)',
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    color: 'var(--color-text-muted)',
                  }}>{role}</span>
                ))}
              </div>
            )}
            <button
              onClick={() => void logout()}
              style={{
                marginTop: '1rem',
                padding: '0.5rem 1.25rem',
                borderRadius: '0.375rem',
                border: '1px solid var(--color-danger)',
                background: 'rgba(239, 68, 68, 0.1)',
                color: 'var(--color-danger)',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.875rem',
                transition: 'all 150ms ease',
              }}
            >
              {t('auth.logout')}
            </button>
          </div>
        </section>
      )}

      {/* App version */}
      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '3rem' }}>
        FLIP v3.0 · Krishi Bhoomi Setu · Built with ❤️ for Indian farmers
      </div>
    </div>
  );
}
