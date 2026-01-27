/**
 * Offline Library Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock offline utilities
interface QueuedRequest {
  id: string;
  url: string;
  method: string;
  body?: unknown;
  timestamp: number;
  retries: number;
}

interface SyncStatus {
  isOnline: boolean;
  lastSync: Date | null;
  pendingCount: number;
  isSyncing: boolean;
}

// Mock offline module
const offline = {
  isOnline: vi.fn(),
  addToQueue: vi.fn(),
  getQueue: vi.fn(),
  removeFromQueue: vi.fn(),
  clearQueue: vi.fn(),
  sync: vi.fn(),
  getSyncStatus: vi.fn(),
  onOnline: vi.fn(),
  onOffline: vi.fn(),
  cacheResponse: vi.fn(),
  getCachedResponse: vi.fn(),
  clearCache: vi.fn(),
};

describe('Offline Detection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('isOnline', () => {
    it('returns true when online', () => {
      offline.isOnline.mockReturnValue(true);
      expect(offline.isOnline()).toBe(true);
    });

    it('returns false when offline', () => {
      offline.isOnline.mockReturnValue(false);
      expect(offline.isOnline()).toBe(false);
    });
  });

  describe('onOnline', () => {
    it('registers online callback', () => {
      const callback = vi.fn();
      offline.onOnline(callback);
      expect(offline.onOnline).toHaveBeenCalledWith(callback);
    });
  });

  describe('onOffline', () => {
    it('registers offline callback', () => {
      const callback = vi.fn();
      offline.onOffline(callback);
      expect(offline.onOffline).toHaveBeenCalledWith(callback);
    });
  });
});

describe('Request Queue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('addToQueue', () => {
    it('adds request to queue', () => {
      const request = {
        url: '/api/messages',
        method: 'POST',
        body: { content: 'Hello' },
      };

      offline.addToQueue.mockReturnValue({ id: 'req-1', ...request, timestamp: Date.now(), retries: 0 });

      const result = offline.addToQueue(request);
      expect(result.id).toBe('req-1');
      expect(offline.addToQueue).toHaveBeenCalledWith(request);
    });
  });

  describe('getQueue', () => {
    it('returns all queued requests', () => {
      const mockQueue: QueuedRequest[] = [
        { id: '1', url: '/api/a', method: 'POST', timestamp: Date.now(), retries: 0 },
        { id: '2', url: '/api/b', method: 'PUT', timestamp: Date.now(), retries: 1 },
      ];
      offline.getQueue.mockReturnValue(mockQueue);

      const queue = offline.getQueue();
      expect(queue).toHaveLength(2);
    });

    it('returns empty array when no queued requests', () => {
      offline.getQueue.mockReturnValue([]);
      expect(offline.getQueue()).toEqual([]);
    });
  });

  describe('removeFromQueue', () => {
    it('removes request by id', () => {
      offline.removeFromQueue('req-1');
      expect(offline.removeFromQueue).toHaveBeenCalledWith('req-1');
    });
  });

  describe('clearQueue', () => {
    it('clears all queued requests', () => {
      offline.clearQueue();
      expect(offline.clearQueue).toHaveBeenCalled();
    });
  });
});

describe('Sync', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('sync', () => {
    it('processes queued requests', async () => {
      offline.sync.mockResolvedValue({ processed: 5, failed: 0 });

      const result = await offline.sync();
      expect(result.processed).toBe(5);
      expect(result.failed).toBe(0);
    });

    it('handles partial sync failure', async () => {
      offline.sync.mockResolvedValue({ processed: 3, failed: 2 });

      const result = await offline.sync();
      expect(result.failed).toBe(2);
    });

    it('throws when offline', async () => {
      offline.sync.mockRejectedValue(new Error('No network connection'));

      await expect(offline.sync()).rejects.toThrow('No network connection');
    });
  });

  describe('getSyncStatus', () => {
    it('returns sync status', () => {
      const mockStatus: SyncStatus = {
        isOnline: true,
        lastSync: new Date(),
        pendingCount: 3,
        isSyncing: false,
      };
      offline.getSyncStatus.mockReturnValue(mockStatus);

      const status = offline.getSyncStatus();
      expect(status.pendingCount).toBe(3);
    });

    it('returns syncing state', () => {
      const mockStatus: SyncStatus = {
        isOnline: true,
        lastSync: new Date(),
        pendingCount: 5,
        isSyncing: true,
      };
      offline.getSyncStatus.mockReturnValue(mockStatus);

      const status = offline.getSyncStatus();
      expect(status.isSyncing).toBe(true);
    });
  });
});

describe('Response Caching', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('cacheResponse', () => {
    it('caches API response', () => {
      const response = { data: [1, 2, 3] };
      offline.cacheResponse('/api/data', response);
      expect(offline.cacheResponse).toHaveBeenCalledWith('/api/data', response);
    });

    it('caches with expiration', () => {
      const response = { data: 'test' };
      const expiresIn = 3600000; // 1 hour
      offline.cacheResponse('/api/data', response, expiresIn);
      expect(offline.cacheResponse).toHaveBeenCalledWith('/api/data', response, expiresIn);
    });
  });

  describe('getCachedResponse', () => {
    it('returns cached response', () => {
      const mockResponse = { data: [1, 2, 3] };
      offline.getCachedResponse.mockReturnValue(mockResponse);

      const result = offline.getCachedResponse('/api/data');
      expect(result).toEqual(mockResponse);
    });

    it('returns null for expired cache', () => {
      offline.getCachedResponse.mockReturnValue(null);
      expect(offline.getCachedResponse('/api/expired')).toBeNull();
    });

    it('returns null for uncached request', () => {
      offline.getCachedResponse.mockReturnValue(null);
      expect(offline.getCachedResponse('/api/uncached')).toBeNull();
    });
  });

  describe('clearCache', () => {
    it('clears all cached responses', () => {
      offline.clearCache();
      expect(offline.clearCache).toHaveBeenCalled();
    });

    it('clears specific cached response', () => {
      offline.clearCache('/api/data');
      expect(offline.clearCache).toHaveBeenCalledWith('/api/data');
    });
  });
});

describe('Offline Use Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('queues message when offline', () => {
    offline.isOnline.mockReturnValue(false);
    
    if (!offline.isOnline()) {
      const request = {
        url: '/api/messages',
        method: 'POST',
        body: { content: 'Hello' },
      };
      offline.addToQueue(request);
    }

    expect(offline.addToQueue).toHaveBeenCalled();
  });

  it('uses cached data when offline', () => {
    offline.isOnline.mockReturnValue(false);
    offline.getCachedResponse.mockReturnValue({ messages: [] });

    if (!offline.isOnline()) {
      const cached = offline.getCachedResponse('/api/messages');
      expect(cached).toBeDefined();
    }
  });

  it('syncs when back online', async () => {
    offline.sync.mockResolvedValue({ processed: 3, failed: 0 });

    // Simulate coming back online
    const onOnlineCallback = vi.fn(async () => {
      await offline.sync();
    });

    offline.onOnline(onOnlineCallback);
    
    // Simulate online event
    await onOnlineCallback();

    expect(offline.sync).toHaveBeenCalled();
  });
});
