/**
 * FLIP v3.0 — i18n Configuration
 * Languages: Hindi (hi), Telugu (te), Tamil (ta), Kannada (kn),
 *            Malayalam (ml), Punjabi (pa), Gujarati (gu), Marathi (mr),
 *            Odia (or), English (en) — fallback.
 * Uses i18next with lazy-loaded JSON namespaces.
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import HttpBackend from 'i18next-http-backend';

// Supported locales — aligned with ADR-014 (10 Indian languages + English)
export const SUPPORTED_LOCALES = [
  { code: 'en', name: 'English', nativeName: 'English', rtl: false },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', rtl: false },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', rtl: false },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', rtl: false },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ', rtl: false },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം', rtl: false },
  { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ', rtl: false },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', rtl: false },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी', rtl: false },
  { code: 'or', name: 'Odia', nativeName: 'ଓଡ଼ିଆ', rtl: false },
] as const;

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]['code'];

i18n
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_LOCALES.map((l) => l.code),
    defaultNS: 'common',
    ns: ['common', 'dashboard', 'advisory', 'disaster', 'copilot', 'settings'],
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
    interpolation: {
      escapeValue: false, // React handles XSS
    },
    react: {
      useSuspense: true,
    },
  });

export default i18n;
