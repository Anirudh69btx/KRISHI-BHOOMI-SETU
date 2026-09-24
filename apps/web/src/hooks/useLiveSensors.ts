/**
 * FLIP v3.0 — WebSocket / NATS-over-WS Live Sensor Hook
 * Connects to the FLIP Core API WebSocket endpoint which proxies
 * NATS JetStream push subscriptions.
 * Subjects: farm.<farm_id>.sensor.processed
 */

import { useEffect, useRef, useCallback } from 'react';
import { useStore } from '../store';
import type { SensorReading } from '@flip/shared-types';

const WS_BASE = import.meta.env.VITE_API_WS_URL ?? 'ws://localhost:8000';

interface UseLiveSensorsOptions {
  farmId: string | null;
  enabled?: boolean;
}

export function useLiveSensors({ farmId, enabled = true }: UseLiveSensorsOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const updateReading = useStore((s) => s.updateReading);
  const isOnline = useStore((s) => s.isOnline);
  const accessToken = useStore((s) => s.accessToken);

  const connect = useCallback(() => {
    if (!farmId || !enabled || !isOnline || !accessToken) return;

    const url = `${WS_BASE}/ws/farms/${farmId}/sensors?token=${accessToken}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.debug(`[WS] Connected to farm ${farmId} sensor stream`);
      // Subscribe to all sensors for this farm
      ws.send(JSON.stringify({ type: 'subscribe', subject: `farm.${farmId}.sensor.processed` }));
    };

    ws.onmessage = (event) => {
      try {
        const reading: SensorReading = JSON.parse(event.data as string);
        updateReading(reading);
      } catch (err) {
        console.error('[WS] Failed to parse sensor reading:', err);
      }
    };

    ws.onclose = (event) => {
      if (!mountedRef.current) return;
      if (!event.wasClean) {
        console.warn(`[WS] Connection closed unexpectedly (${event.code}), reconnecting in 3s...`);
        reconnectTimer.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = (err) => {
      console.error('[WS] Error:', err);
      ws.close();
    };
  }, [farmId, enabled, isOnline, accessToken, updateReading]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
    };
  }, [connect]);

  const send = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return { send };
}
