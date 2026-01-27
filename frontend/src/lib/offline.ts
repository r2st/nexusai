/**
 * Offline Support Library
 * 
 * Provides caching and offline functionality for the desktop app.
 * Uses IndexedDB for persistent storage and service workers for caching.
 */

// =============================================================================
// Types
// =============================================================================

export interface CachedConversation {
  id: string;
  title: string;
  messages: CachedMessage[];
  updatedAt: string;
  syncedAt?: string;
}

export interface CachedMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface OfflineQueueItem {
  id: string;
  type: 'message' | 'conversation' | 'feedback';
  data: unknown;
  createdAt: string;
  retries: number;
}

// =============================================================================
// IndexedDB Setup
// =============================================================================

const DB_NAME = 'nexusai-offline';
const DB_VERSION = 1;

const STORES = {
  conversations: 'conversations',
  messages: 'messages',
  queue: 'offline-queue',
  settings: 'settings',
} as const;

let db: IDBDatabase | null = null;

async function openDatabase(): Promise<IDBDatabase> {
  if (db) return db;

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      db = request.result;
      resolve(db);
    };

    request.onupgradeneeded = (event) => {
      const database = (event.target as IDBOpenDBRequest).result;

      // Conversations store
      if (!database.objectStoreNames.contains(STORES.conversations)) {
        const convStore = database.createObjectStore(STORES.conversations, { keyPath: 'id' });
        convStore.createIndex('updatedAt', 'updatedAt');
      }

      // Messages store
      if (!database.objectStoreNames.contains(STORES.messages)) {
        const msgStore = database.createObjectStore(STORES.messages, { keyPath: 'id' });
        msgStore.createIndex('conversationId', 'conversationId');
        msgStore.createIndex('timestamp', 'timestamp');
      }

      // Offline queue store
      if (!database.objectStoreNames.contains(STORES.queue)) {
        const queueStore = database.createObjectStore(STORES.queue, { keyPath: 'id' });
        queueStore.createIndex('createdAt', 'createdAt');
      }

      // Settings store
      if (!database.objectStoreNames.contains(STORES.settings)) {
        database.createObjectStore(STORES.settings, { keyPath: 'key' });
      }
    };
  });
}

// =============================================================================
// Conversation Cache
// =============================================================================

export async function cacheConversation(conversation: CachedConversation): Promise<void> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.conversations, 'readwrite');
  const store = tx.objectStore(STORES.conversations);

  return new Promise((resolve, reject) => {
    const request = store.put({
      ...conversation,
      syncedAt: new Date().toISOString(),
    });
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export async function getCachedConversation(id: string): Promise<CachedConversation | null> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.conversations, 'readonly');
  const store = tx.objectStore(STORES.conversations);

  return new Promise((resolve, reject) => {
    const request = store.get(id);
    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error);
  });
}

export async function getAllCachedConversations(): Promise<CachedConversation[]> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.conversations, 'readonly');
  const store = tx.objectStore(STORES.conversations);
  const index = store.index('updatedAt');

  return new Promise((resolve, reject) => {
    const request = index.getAll();
    request.onsuccess = () => resolve(request.result.reverse()); // Newest first
    request.onerror = () => reject(request.error);
  });
}

export async function deleteCachedConversation(id: string): Promise<void> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.conversations, 'readwrite');
  const store = tx.objectStore(STORES.conversations);

  return new Promise((resolve, reject) => {
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// =============================================================================
// Message Cache
// =============================================================================

export async function cacheMessage(
  conversationId: string,
  message: CachedMessage
): Promise<void> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.messages, 'readwrite');
  const store = tx.objectStore(STORES.messages);

  return new Promise((resolve, reject) => {
    const request = store.put({
      ...message,
      conversationId,
    });
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export async function getCachedMessages(conversationId: string): Promise<CachedMessage[]> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.messages, 'readonly');
  const store = tx.objectStore(STORES.messages);
  const index = store.index('conversationId');

  return new Promise((resolve, reject) => {
    const request = index.getAll(conversationId);
    request.onsuccess = () => {
      const messages = request.result.sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );
      resolve(messages);
    };
    request.onerror = () => reject(request.error);
  });
}

// =============================================================================
// Offline Queue
// =============================================================================

export async function addToOfflineQueue(item: Omit<OfflineQueueItem, 'id' | 'createdAt' | 'retries'>): Promise<string> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.queue, 'readwrite');
  const store = tx.objectStore(STORES.queue);

  const id = `queue-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const queueItem: OfflineQueueItem = {
    ...item,
    id,
    createdAt: new Date().toISOString(),
    retries: 0,
  };

  return new Promise((resolve, reject) => {
    const request = store.add(queueItem);
    request.onsuccess = () => resolve(id);
    request.onerror = () => reject(request.error);
  });
}

export async function getOfflineQueue(): Promise<OfflineQueueItem[]> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.queue, 'readonly');
  const store = tx.objectStore(STORES.queue);
  const index = store.index('createdAt');

  return new Promise((resolve, reject) => {
    const request = index.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function removeFromOfflineQueue(id: string): Promise<void> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.queue, 'readwrite');
  const store = tx.objectStore(STORES.queue);

  return new Promise((resolve, reject) => {
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export async function updateQueueItemRetries(id: string, retries: number): Promise<void> {
  const database = await openDatabase();
  const tx = database.transaction(STORES.queue, 'readwrite');
  const store = tx.objectStore(STORES.queue);

  return new Promise((resolve, reject) => {
    const getRequest = store.get(id);
    getRequest.onsuccess = () => {
      const item = getRequest.result;
      if (item) {
        item.retries = retries;
        const putRequest = store.put(item);
        putRequest.onsuccess = () => resolve();
        putRequest.onerror = () => reject(putRequest.error);
      } else {
        resolve();
      }
    };
    getRequest.onerror = () => reject(getRequest.error);
  });
}

// =============================================================================
// Sync Manager
// =============================================================================

export class OfflineSyncManager {
  private isOnline = navigator.onLine;
  private syncInProgress = false;
  private listeners: Set<(online: boolean) => void> = new Set();

  constructor() {
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());
  }

  private handleOnline(): void {
    this.isOnline = true;
    this.notifyListeners();
    this.processQueue();
  }

  private handleOffline(): void {
    this.isOnline = false;
    this.notifyListeners();
  }

  private notifyListeners(): void {
    this.listeners.forEach((listener) => listener(this.isOnline));
  }

  onStatusChange(callback: (online: boolean) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  getStatus(): boolean {
    return this.isOnline;
  }

  async processQueue(): Promise<void> {
    if (!this.isOnline || this.syncInProgress) return;

    this.syncInProgress = true;

    try {
      const queue = await getOfflineQueue();

      for (const item of queue) {
        if (item.retries >= 3) {
          // Remove items that have failed too many times
          await removeFromOfflineQueue(item.id);
          continue;
        }

        try {
          await this.processQueueItem(item);
          await removeFromOfflineQueue(item.id);
        } catch (error) {
          console.error('Failed to process queue item:', error);
          await updateQueueItemRetries(item.id, item.retries + 1);
        }
      }
    } finally {
      this.syncInProgress = false;
    }
  }

  private async processQueueItem(item: OfflineQueueItem): Promise<void> {
    // Override this in your app to handle different queue item types
    console.log('Processing queue item:', item);
    
    switch (item.type) {
      case 'message':
        // Send message to server
        break;
      case 'conversation':
        // Sync conversation
        break;
      case 'feedback':
        // Send feedback
        break;
    }
  }
}

// Singleton instance
export const offlineSyncManager = new OfflineSyncManager();

// =============================================================================
// Storage Stats
// =============================================================================

export async function getStorageStats(): Promise<{
  conversations: number;
  messages: number;
  queueItems: number;
  estimatedSize: number;
}> {
  const database = await openDatabase();

  const countStore = async (storeName: string): Promise<number> => {
    const tx = database.transaction(storeName, 'readonly');
    const store = tx.objectStore(storeName);
    return new Promise((resolve, reject) => {
      const request = store.count();
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  };

  const [conversations, messages, queueItems] = await Promise.all([
    countStore(STORES.conversations),
    countStore(STORES.messages),
    countStore(STORES.queue),
  ]);

  // Estimate size (rough calculation)
  const estimatedSize = (conversations * 2000) + (messages * 500) + (queueItems * 1000);

  return { conversations, messages, queueItems, estimatedSize };
}

export async function clearAllCachedData(): Promise<void> {
  const database = await openDatabase();

  const clearStore = (storeName: string): Promise<void> => {
    const tx = database.transaction(storeName, 'readwrite');
    const store = tx.objectStore(storeName);
    return new Promise((resolve, reject) => {
      const request = store.clear();
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  };

  await Promise.all([
    clearStore(STORES.conversations),
    clearStore(STORES.messages),
    clearStore(STORES.queue),
  ]);
}

export default {
  cacheConversation,
  getCachedConversation,
  getAllCachedConversations,
  deleteCachedConversation,
  cacheMessage,
  getCachedMessages,
  addToOfflineQueue,
  getOfflineQueue,
  removeFromOfflineQueue,
  offlineSyncManager,
  getStorageStats,
  clearAllCachedData,
};
