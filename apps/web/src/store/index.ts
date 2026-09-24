/**
 * FLIP v3.0 — Zustand Global Store
 * Manages: auth session, farm selection, sensor live data, offline sync queue,
 *          disaster alerts, copilot conversation, i18n locale.
 */

import { create } from 'zustand';
import { subscribeWithSelector, persist, devtools } from 'zustand/middleware';
import type {
  SensorReading,
  Farm,
  Advisory,
  DisasterAlert,
  UserProfile,
} from '@flip/shared-types';

// ─── Auth Slice ──────────────────────────────────────────────────────────────
interface AuthState {
  user: UserProfile | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  setAuth: (user: UserProfile, token: string) => void;
  clearAuth: () => void;
}

// ─── Farm Slice ──────────────────────────────────────────────────────────────
interface FarmState {
  farms: Farm[];
  activeFarmId: string | null;
  setFarms: (farms: Farm[]) => void;
  setActiveFarm: (farmId: string) => void;
  activeFarm: () => Farm | undefined;
}

// ─── Sensor Slice ─────────────────────────────────────────────────────────────
interface SensorState {
  liveReadings: Record<string, SensorReading>; // keyed by sensor_id
  readingHistory: Record<string, SensorReading[]>; // last 100 per sensor
  updateReading: (reading: SensorReading) => void;
  clearReadings: (farmId: string) => void;
}

// ─── Advisory Slice ──────────────────────────────────────────────────────────
interface AdvisoryState {
  advisories: Advisory[];
  unreadCount: number;
  setAdvisories: (advisories: Advisory[]) => void;
  markRead: (advisoryId: string) => void;
}

// ─── Disaster Slice ──────────────────────────────────────────────────────────
interface DisasterState {
  activeAlerts: DisasterAlert[];
  dismissedAlertIds: Set<string>;
  setAlerts: (alerts: DisasterAlert[]) => void;
  dismissAlert: (alertId: string) => void;
}

// ─── Copilot Slice ────────────────────────────────────────────────────────────
interface CopilotMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  language: string;
}

interface CopilotState {
  messages: CopilotMessage[];
  isListening: boolean;
  isSpeaking: boolean;
  isOpen: boolean;
  addMessage: (msg: Omit<CopilotMessage, 'id' | 'timestamp'>) => void;
  setListening: (v: boolean) => void;
  setSpeaking: (v: boolean) => void;
  toggleOpen: () => void;
  clearMessages: () => void;
}

// ─── Offline Slice ────────────────────────────────────────────────────────────
interface OfflineAction {
  id: string;
  type: string;
  payload: unknown;
  createdAt: Date;
  retries: number;
}

interface OfflineState {
  isOnline: boolean;
  pendingActions: OfflineAction[];
  setOnline: (v: boolean) => void;
  enqueueAction: (action: Omit<OfflineAction, 'id' | 'createdAt' | 'retries'>) => void;
  dequeueAction: (id: string) => void;
  pendingCount: () => number;
}

// ─── UI Slice ─────────────────────────────────────────────────────────────────
interface UIState {
  locale: 'en' | 'hi' | 'te' | 'ta' | 'kn' | 'ml' | 'pa' | 'gu' | 'mr' | 'or';
  sidebarOpen: boolean;
  mapStyle: 'satellite' | 'terrain' | 'street';
  setLocale: (locale: UIState['locale']) => void;
  setSidebar: (open: boolean) => void;
  setMapStyle: (style: UIState['mapStyle']) => void;
}

// ─── Combined Store ───────────────────────────────────────────────────────────
type StoreState = AuthState &
  FarmState &
  SensorState &
  AdvisoryState &
  DisasterState &
  CopilotState &
  OfflineState &
  UIState;

export const useStore = create<StoreState>()(
  devtools(
    persist(
      subscribeWithSelector((set, get) => ({
        // ── Auth ──────────────────────────────────────────────────────────────
        user: null,
        accessToken: null,
        isAuthenticated: false,
        setAuth: (user, accessToken) => set({ user, accessToken, isAuthenticated: true }),
        clearAuth: () => set({ user: null, accessToken: null, isAuthenticated: false }),

        // ── Farm ──────────────────────────────────────────────────────────────
        farms: [],
        activeFarmId: null,
        setFarms: (farms) => set({ farms }),
        setActiveFarm: (farmId) => set({ activeFarmId: farmId }),
        activeFarm: () => {
          const { farms, activeFarmId } = get();
          return farms.find((f) => f.id === activeFarmId);
        },

        // ── Sensors ───────────────────────────────────────────────────────────
        liveReadings: {},
        readingHistory: {},
        updateReading: (reading) =>
          set((state) => {
            const key = `${reading.device_id}_${reading.sensor_type}`;
            const history = state.readingHistory[key] ?? [];
            return {
              liveReadings: { ...state.liveReadings, [key]: reading },
              readingHistory: {
                ...state.readingHistory,
                [key]: [reading, ...history].slice(0, 100),
              },
            };
          }),
        clearReadings: (farmId) =>
          set((state) => {
            // Remove readings for all sensors of this farm
            const filtered = Object.fromEntries(
              Object.entries(state.liveReadings).filter(([, r]) => r.farm_id !== farmId),
            );
            return { liveReadings: filtered };
          }),

        // ── Advisories ────────────────────────────────────────────────────────
        advisories: [],
        unreadCount: 0,
        setAdvisories: (advisories) =>
          set({ advisories, unreadCount: advisories.filter((a) => a.status === 'ACTIVE').length }),
        markRead: (advisoryId) =>
          set((state) => ({
            advisories: state.advisories.map((a) =>
              a.id === advisoryId ? { ...a, status: 'ACKNOWLEDGED' as const } : a,
            ),
            unreadCount: Math.max(0, state.unreadCount - 1),
          })),

        // ── Disaster ──────────────────────────────────────────────────────────
        activeAlerts: [],
        dismissedAlertIds: new Set(),
        setAlerts: (alerts) => set({ activeAlerts: alerts }),
        dismissAlert: (alertId) =>
          set((state) => ({
            dismissedAlertIds: new Set([...state.dismissedAlertIds, alertId]),
          })),

        // ── Copilot ───────────────────────────────────────────────────────────
        messages: [],
        isListening: false,
        isSpeaking: false,
        isOpen: false,
        addMessage: (msg) =>
          set((state) => ({
            messages: [
              ...state.messages,
              { ...msg, id: crypto.randomUUID(), timestamp: new Date() },
            ],
          })),
        setListening: (isListening) => set({ isListening }),
        setSpeaking: (isSpeaking) => set({ isSpeaking }),
        toggleOpen: () => set((s) => ({ isOpen: !s.isOpen })),
        clearMessages: () => set({ messages: [] }),

        // ── Offline ───────────────────────────────────────────────────────────
        isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
        pendingActions: [],
        setOnline: (isOnline) => set({ isOnline }),
        enqueueAction: (action) =>
          set((state) => ({
            pendingActions: [
              ...state.pendingActions,
              { ...action, id: crypto.randomUUID(), createdAt: new Date(), retries: 0 },
            ],
          })),
        dequeueAction: (id) =>
          set((state) => ({
            pendingActions: state.pendingActions.filter((a) => a.id !== id),
          })),
        pendingCount: () => get().pendingActions.length,

        // ── UI ────────────────────────────────────────────────────────────────
        locale: 'en',
        sidebarOpen: false,
        mapStyle: 'satellite',
        setLocale: (locale) => set({ locale }),
        setSidebar: (sidebarOpen) => set({ sidebarOpen }),
        setMapStyle: (mapStyle) => set({ mapStyle }),
      })),
      {
        name: 'flip-store',
        // Only persist UI preferences and offline queue (not live sensor data)
        partialize: (state) => ({
          locale: state.locale,
          activeFarmId: state.activeFarmId,
          mapStyle: state.mapStyle,
          pendingActions: state.pendingActions,
          dismissedAlertIds: Array.from(state.dismissedAlertIds),
        }),
      },
    ),
    { name: 'FLIP Store' },
  ),
);

// ─── Derived Selectors ────────────────────────────────────────────────────────
export const selectLiveReading = (sensorId: string) => (state: StoreState) =>
  state.liveReadings[sensorId];

export const selectActiveFarm = (state: StoreState) =>
  state.farms.find((f) => f.id === state.activeFarmId);

export const selectPendingCount = (state: StoreState) => state.pendingActions.length;

export const selectUnreadAdvisories = (state: StoreState) =>
  state.advisories.filter((a) => a.status === 'ACTIVE');

export const selectCriticalAlerts = (state: StoreState) =>
  state.activeAlerts.filter(
    (a) => (a.severity === 'EMERGENCY' || a.severity === 'WARNING') && !state.dismissedAlertIds.has(a.id),
  );
