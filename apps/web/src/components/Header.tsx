/**
 * FLIP v3.0 — Platform Navigation Header (Segment 01)
 * Displays User Avatar, Role Badge, Navigation Links, Language Switcher & Logout.
 */

import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';
import '../auth/authStyles.css';

export const Header: React.FC = () => {
  const { user, profile, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const role = profile?.role || 'farmer';
  const fullName = profile?.full_name || user?.profile.name || 'Farmer';
  const initials = fullName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const navLinks = [
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'Farms', path: '/farms' },
    { label: 'Advisories', path: '/advisories' },
    { label: 'Disaster Alerts', path: '/disaster' },
  ];

  return (
    <header
      style={{
        background: '#064e3b',
        color: '#ffffff',
        borderBottom: '1px solid #047857',
        padding: '0.75rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
      }}
    >
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        <Link
          to="/dashboard"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.625rem',
            color: '#ffffff',
            textDecoration: 'none',
          }}
        >
          <span style={{ fontSize: '1.75rem' }}>🌾</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.125rem', letterSpacing: '-0.01em', lineHeight: 1.2 }}>
              KRISHI BHOOMI SETU
            </div>
            <div style={{ fontSize: '0.6875rem', color: '#a7f3d0', fontWeight: 600 }}>
              FLIP v3.0 Intelligence
            </div>
          </div>
        </Link>

        {/* Navigation Links */}
        {isAuthenticated && (
          <nav style={{ display: 'flex', gap: '0.5rem' }}>
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  style={{
                    color: isActive ? '#ffffff' : '#d1fae5',
                    background: isActive ? 'rgba(255, 255, 255, 0.15)' : 'transparent',
                    padding: '0.4rem 0.85rem',
                    borderRadius: '0.5rem',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    textDecoration: 'none',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        )}
      </div>

      {/* Right User Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {isAuthenticated ? (
          <>
            {/* Role Badge */}
            <span className={`flip-role-badge ${role}`}>
              {role === 'farmer'
                ? '🌾 Farmer'
                : role === 'agronomist'
                ? '🔬 Agronomist'
                : role === 'fpo_admin'
                ? '🏢 FPO Admin'
                : role === 'gov_officer'
                ? '🏛️ Govt Officer'
                : `🛡️ ${role}`}
            </span>

            {/* Profile Avatar / Link */}
            <button
              type="button"
              onClick={() => navigate('/profile')}
              title={`View Profile: ${fullName}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.625rem',
                background: 'rgba(255, 255, 255, 0.12)',
                border: '1px solid rgba(255, 255, 255, 0.25)',
                borderRadius: '2rem',
                padding: '0.25rem 0.75rem 0.25rem 0.35rem',
                cursor: 'pointer',
                color: '#ffffff',
              }}
            >
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: '#10b981',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '0.8125rem',
                }}
              >
                {initials || 'U'}
              </div>
              <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>{fullName}</span>
            </button>

            {/* Logout Button */}
            <button
              type="button"
              onClick={logout}
              style={{
                background: 'transparent',
                border: '1px solid #ef4444',
                color: '#fca5a5',
                padding: '0.375rem 0.75rem',
                borderRadius: '0.5rem',
                fontSize: '0.8125rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#ef4444';
                e.currentTarget.style.color = '#ffffff';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = '#fca5a5';
              }}
            >
              Logout
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="flip-btn-primary"
            style={{ width: 'auto', padding: '0.5rem 1.25rem', fontSize: '0.875rem' }}
          >
            Log In
          </button>
        )}
      </div>
    </header>
  );
};

export default Header;
