/**
 * FLIP v3.0 — ProtectedRoute Route Guard (Segment 01)
 * Enforces authenticated session & optional role permissions for route navigation.
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles,
}) => {
  const { isAuthenticated, isLoading, hasAnyRole } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#064e3b',
          color: '#ffffff',
        }}
      >
        <div
          style={{
            width: '40px',
            height: '40px',
            border: '3px solid rgba(255,255,255,0.2)',
            borderTop: '3px solid #ffffff',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            marginBottom: '1rem',
          }}
        />
        <p style={{ fontWeight: 600 }}>Loading FLIP Session...</p>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page and preserve attempt location
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRoles && requiredRoles.length > 0 && !hasAnyRole(requiredRoles)) {
    // Insufficient roles
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
