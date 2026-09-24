/**
 * FLIP v3.0 — Root App Component (Segment 01)
 * Integrates AuthProvider, Keycloak OIDC flows, Header, ProtectedRoute, and Role-gated views.
 */

import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';

// i18n initialization
import './i18n';

import { AuthProvider } from './auth/AuthProvider';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Header } from './components/Header';
import { useOfflineSync } from './hooks/useOfflineSync';

import { LoginPage } from './auth/LoginPage';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { ProfilePage } from './auth/ProfilePage';
import { DashboardPage } from './pages/DashboardPage';
import { KisanVoiceCopilot } from './components/KisanVoiceCopilot';

// Lazy-loaded routes
const FarmsPage = lazy(() => import('./pages/FarmsPage').then((m) => ({ default: m.FarmsPage })));
const AdvisoriesPage = lazy(() => import('./pages/AdvisoriesPage').then((m) => ({ default: m.AdvisoriesPage })));
const DisasterPage = lazy(() => import('./pages/DisasterPage').then((m) => ({ default: m.DisasterPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));

function UnauthorizedScreen() {
  return (
    <div
      style={{
        minHeight: '70vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '2rem',
      }}
    >
      <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🛑</div>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#991b1b', margin: '0 0 0.5rem' }}>
        403 — Unauthorized Access
      </h1>
      <p style={{ color: '#4b5563', maxWidth: '480px', marginBottom: '1.5rem' }}>
        Your account role does not have permission to view this module. If you believe this is an error, please contact your FPO administrator.
      </p>
      <Link
        to="/dashboard"
        style={{
          background: '#059669',
          color: '#ffffff',
          padding: '0.625rem 1.25rem',
          borderRadius: '0.5rem',
          fontWeight: 600,
          textDecoration: 'none',
        }}
      >
        Return to Dashboard
      </Link>
    </div>
  );
}

function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header />
      <main style={{ flex: 1, background: '#f8fafc' }}>
        {children}
      </main>
      <KisanVoiceCopilot />
    </div>
  );
}

function AppContent() {
  useOfflineSync();

  return (
    <Routes>
      {/* Public Authentication Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/unauthorized" element={<UnauthorizedScreen />} />

      {/* Protected Application Routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout>
              <DashboardPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <MainLayout>
              <DashboardPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/farms"
        element={
          <ProtectedRoute>
            <MainLayout>
              <FarmsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/advisories"
        element={
          <ProtectedRoute>
            <MainLayout>
              <AdvisoriesPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/disaster"
        element={
          <ProtectedRoute>
            <MainLayout>
              <DisasterPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ProfilePage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <MainLayout>
              <SettingsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense
          fallback={
            <div
              style={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#064e3b',
                color: '#ffffff',
              }}
            >
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🌾</div>
                <div style={{ fontWeight: 600 }}>Loading FLIP v3.0...</div>
              </div>
            </div>
          }
        >
          <AppContent />
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
