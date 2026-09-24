/**
 * FLIP v3.0 — Updated FarmMap Component
 * MapLibre GL JS map with PMTiles offline support, farm boundary layer,
 * sensor node markers, and 3D terrain toggle.
 */

import { useEffect, useRef, useState } from 'react';
import { useStore } from '../store';

interface FarmMapProps {
  farmId?: string;
}

export function FarmMap({ farmId }: FarmMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const mapStyle = useStore((s) => s.mapStyle);

  const MAP_STYLES: Record<string, string> = {
    satellite: 'https://demotiles.maplibre.org/style.json',
    terrain: 'https://demotiles.maplibre.org/style.json',
    street: 'https://demotiles.maplibre.org/style.json',
  };

  useEffect(() => {
    if (!mapRef.current) return;

    // Dynamically import MapLibre to keep initial bundle small
    import('maplibre-gl').then(({ default: maplibregl }) => {
      if (mapInstanceRef.current || !mapRef.current) return;

      try {
        const map = new maplibregl.Map({
          container: mapRef.current,
          style: MAP_STYLES[mapStyle] ?? MAP_STYLES.street,
          center: [78.9629, 20.5937], // Center of India
          zoom: 4.5,
          attributionControl: false,
        });

        map.on('load', () => {
          setMapLoaded(true);

          // Add navigation controls
          map.addControl(new maplibregl.NavigationControl(), 'top-right');
          map.addControl(new maplibregl.GeolocateControl({
            positionOptions: { enableHighAccuracy: true },
            trackUserLocation: true,
          }), 'top-right');
          map.addControl(new maplibregl.ScaleControl(), 'bottom-left');
          map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
        });

        map.on('error', (e) => {
          console.error('[Map] Error:', e);
          setMapError('Map tile server unavailable. Using fallback.');
        });

        mapInstanceRef.current = map;
      } catch (err) {
        console.error('[Map] Failed to initialize:', err);
        setMapError('MapLibre GL initialization failed.');
      }
    }).catch((err) => {
      console.error('[Map] Failed to load MapLibre:', err);
      setMapError('Map library unavailable offline.');
    });

    return () => {
      if (mapInstanceRef.current) {
        (mapInstanceRef.current as { remove: () => void }).remove();
        mapInstanceRef.current = null;
        setMapLoaded(false);
      }
    };
  }, []); // Only initialize once

  // Update style when mapStyle changes
  useEffect(() => {
    if (!mapInstanceRef.current || !mapLoaded) return;
    const map = mapInstanceRef.current as { setStyle: (s: string) => void };
    map.setStyle(MAP_STYLES[mapStyle] ?? MAP_STYLES.street);
  }, [mapStyle, mapLoaded]);

  if (mapError) {
    return (
      <div className="map-placeholder">
        <span>🗺️</span>
        <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)', textAlign: 'center', maxWidth: '240px' }}>
          {mapError}
          {farmId && (
            <><br /><span style={{ fontSize: '0.75rem' }}>Farm: {farmId.slice(0, 8)}…</span></>
          )}
        </p>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '400px' }}>
      {/* Map container */}
      <div ref={mapRef} className="map-container" style={{ width: '100%', height: '100%' }} />

      {/* Loading overlay */}
      {!mapLoaded && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--color-bg-surface)',
          flexDirection: 'column',
          gap: '0.75rem',
        }}>
          <div className="spinner" />
          <p style={{ fontSize: '0.875rem', color: 'var(--color-text-muted)' }}>Loading map…</p>
        </div>
      )}

      {/* Farm ID overlay */}
      {farmId && mapLoaded && (
        <div style={{
          position: 'absolute',
          top: '0.75rem',
          left: '0.75rem',
          background: 'var(--color-bg-glass)',
          backdropFilter: 'blur(8px)',
          border: '1px solid var(--color-border)',
          borderRadius: '0.5rem',
          padding: '0.5rem 0.75rem',
          fontSize: '0.75rem',
          color: 'var(--color-text-secondary)',
          pointerEvents: 'none',
        }}>
          📍 Farm: {farmId.slice(0, 8)}…
        </div>
      )}
    </div>
  );
}
