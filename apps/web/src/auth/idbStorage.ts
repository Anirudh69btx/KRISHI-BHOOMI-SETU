/**
 * FLIP v3.0 — Encrypted IndexedDB Storage & Offline Mutation Queue (Segment 01)
 * Enforces ADR-004 Offline-First: Encrypted token cache + Background Sync mutation queue.
 */

const DB_NAME = 'flip_offline_store';
const DB_VERSION = 1;
const STORE_AUTH = 'auth_tokens';
const STORE_MUTATIONS = 'pending_mutations';

export interface PendingMutation {
  id: string;
  url: string;
  method: 'POST' | 'PUT' | 'DELETE';
  body?: any;
  headers?: Record<string, string>;
  queuedAt: string;
  retryCount: number;
}

// Open IndexedDB database with object stores
function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      reject(new Error('IndexedDB not available'));
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_AUTH)) {
        db.createObjectStore(STORE_AUTH, { keyPath: 'key' });
      }
      if (!db.objectStoreNames.contains(STORE_MUTATIONS)) {
        db.createObjectStore(STORE_MUTATIONS, { keyPath: 'id' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Web Crypto API Key derivation for AES-GCM token encryption
async function getCryptoKey(): Promise<CryptoKey> {
  let rawSecret = localStorage.getItem('flip_crypto_device_seed');
  if (!rawSecret) {
    const randomBytes = new Uint8Array(32);
    crypto.getRandomValues(randomBytes);
    rawSecret = Array.from(randomBytes).map((b) => b.toString(16).padStart(2, '0')).join('');
    localStorage.setItem('flip_crypto_device_seed', rawSecret);
  }

  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(rawSecret),
    { name: 'PBKDF2' },
    false,
    ['deriveKey'],
  );

  return await crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: encoder.encode('flip-offline-salt-2026'),
      iterations: 10000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

// Encrypt plaintext with AES-GCM
async function encryptData(plaintext: string): Promise<string> {
  const key = await getCryptoKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(plaintext);

  const ciphertext = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    encoded,
  );

  const combined = new Uint8Array(iv.length + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), iv.length);

  return btoa(String.fromCharCode(...combined));
}

// Decrypt AES-GCM ciphertext
async function decryptData(encodedStr: string): Promise<string> {
  const binary = atob(encodedStr);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }

  const iv = bytes.slice(0, 12);
  const ciphertext = bytes.slice(12);
  const key = await getCryptoKey();

  const decrypted = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv },
    key,
    ciphertext,
  );

  return new TextDecoder().decode(decrypted);
}

/**
 * Encrypted IndexedDB token storage interface (compatible with oidc-client-ts StateStore)
 */
export const idbTokenStore = {
  async set(key: string, value: string): Promise<void> {
    const db = await openDb();
    const encrypted = await encryptData(value);
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_AUTH, 'readwrite');
      const store = tx.objectStore(STORE_AUTH);
      store.put({ key, value: encrypted });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  },

  async get(key: string): Promise<string | null> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_AUTH, 'readonly');
      const store = tx.objectStore(STORE_AUTH);
      const req = store.get(key);
      req.onsuccess = async () => {
        if (!req.result?.value) {
          resolve(null);
          return;
        }
        try {
          const decrypted = await decryptData(req.result.value);
          resolve(decrypted);
        } catch (e) {
          console.error('[IDB] Decryption failed:', e);
          resolve(null);
        }
      };
      req.onerror = () => reject(req.error);
    });
  },

  async remove(key: string): Promise<void> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_AUTH, 'readwrite');
      const store = tx.objectStore(STORE_AUTH);
      store.delete(key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  },

  async getAllKeys(): Promise<string[]> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_AUTH, 'readonly');
      const store = tx.objectStore(STORE_AUTH);
      const req = store.getAllKeys();
      req.onsuccess = () => resolve(req.result.map(String));
      req.onerror = () => reject(req.error);
    });
  },
};

/**
 * Offline Mutation Queue for Background Sync
 */
export const mutationQueue = {
  async queue(url: string, method: 'POST' | 'PUT' | 'DELETE', body?: any, headers?: Record<string, string>): Promise<string> {
    const db = await openDb();
    const id = `mut_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const mutation: PendingMutation = {
      id,
      url,
      method,
      body,
      headers,
      queuedAt: new Date().toISOString(),
      retryCount: 0,
    };

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_MUTATIONS, 'readwrite');
      const store = tx.objectStore(STORE_MUTATIONS);
      store.put(mutation);
      tx.oncomplete = () => {
        // Request Background Sync if supported by Service Worker
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
          navigator.serviceWorker.ready.then((reg: any) => {
            reg.sync?.register('flip-background-sync').catch(() => {});
          });
        }
        resolve(id);
      };
      tx.onerror = () => reject(tx.error);
    });
  },

  async getPending(): Promise<PendingMutation[]> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_MUTATIONS, 'readonly');
      const store = tx.objectStore(STORE_MUTATIONS);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  },

  async remove(id: string): Promise<void> {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_MUTATIONS, 'readwrite');
      const store = tx.objectStore(STORE_MUTATIONS);
      store.delete(id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  },
};
