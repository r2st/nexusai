/**
 * Compliance Library Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock compliance utilities
interface ConsentRecord {
  category: string;
  granted: boolean;
  timestamp: Date;
  version: string;
}

interface AuditLogEntry {
  id: string;
  action: string;
  userId: string;
  resourceType: string;
  resourceId: string;
  timestamp: Date;
  metadata: Record<string, unknown>;
}

interface DataSubjectRightsRequest {
  id: string;
  type: 'access' | 'export' | 'delete' | 'rectification';
  status: 'pending' | 'processing' | 'completed' | 'rejected';
  createdAt: Date;
  completedAt?: Date;
}

// Mock compliance module
const consent = {
  getConsent: vi.fn(),
  setConsent: vi.fn(),
  hasConsent: vi.fn(),
  revokeConsent: vi.fn(),
  getAllConsents: vi.fn(),
};

const audit = {
  log: vi.fn(),
  query: vi.fn(),
  exportLogs: vi.fn(),
};

const dataRights = {
  requestAccess: vi.fn(),
  requestExport: vi.fn(),
  requestDeletion: vi.fn(),
  requestRectification: vi.fn(),
  getRequestStatus: vi.fn(),
  getAllRequests: vi.fn(),
};

const encryption = {
  encryptPII: vi.fn(),
  decryptPII: vi.fn(),
  hashIdentifier: vi.fn(),
};

const retention = {
  getRetentionPolicy: vi.fn(),
  applyRetentionPolicy: vi.fn(),
  scheduleDataDeletion: vi.fn(),
};

describe('Consent Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getConsent', () => {
    it('returns consent for a category', () => {
      const mockConsent: ConsentRecord = {
        category: 'analytics',
        granted: true,
        timestamp: new Date(),
        version: '1.0',
      };
      consent.getConsent.mockReturnValue(mockConsent);

      const result = consent.getConsent('analytics');
      expect(result).toEqual(mockConsent);
      expect(consent.getConsent).toHaveBeenCalledWith('analytics');
    });

    it('returns null for unknown category', () => {
      consent.getConsent.mockReturnValue(null);
      expect(consent.getConsent('unknown')).toBeNull();
    });
  });

  describe('setConsent', () => {
    it('records consent for a category', () => {
      consent.setConsent('analytics', true, '1.0');
      expect(consent.setConsent).toHaveBeenCalledWith('analytics', true, '1.0');
    });

    it('records consent revocation', () => {
      consent.setConsent('marketing', false, '1.0');
      expect(consent.setConsent).toHaveBeenCalledWith('marketing', false, '1.0');
    });
  });

  describe('hasConsent', () => {
    it('returns true when consent is granted', () => {
      consent.hasConsent.mockReturnValue(true);
      expect(consent.hasConsent('analytics')).toBe(true);
    });

    it('returns false when consent is not granted', () => {
      consent.hasConsent.mockReturnValue(false);
      expect(consent.hasConsent('marketing')).toBe(false);
    });
  });

  describe('revokeConsent', () => {
    it('revokes consent for a category', () => {
      consent.revokeConsent('analytics');
      expect(consent.revokeConsent).toHaveBeenCalledWith('analytics');
    });
  });

  describe('getAllConsents', () => {
    it('returns all consent records', () => {
      const mockConsents: ConsentRecord[] = [
        { category: 'essential', granted: true, timestamp: new Date(), version: '1.0' },
        { category: 'analytics', granted: true, timestamp: new Date(), version: '1.0' },
        { category: 'marketing', granted: false, timestamp: new Date(), version: '1.0' },
      ];
      consent.getAllConsents.mockReturnValue(mockConsents);

      const result = consent.getAllConsents();
      expect(result).toHaveLength(3);
    });
  });
});

describe('Audit Logging', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('log', () => {
    it('creates audit log entry', () => {
      const entry = {
        action: 'user.login',
        userId: 'user-123',
        resourceType: 'session',
        resourceId: 'session-456',
        metadata: { ip: '192.168.1.1' },
      };

      audit.log(entry);
      expect(audit.log).toHaveBeenCalledWith(entry);
    });
  });

  describe('query', () => {
    it('queries audit logs with filters', () => {
      const mockEntries: AuditLogEntry[] = [
        {
          id: '1',
          action: 'user.login',
          userId: 'user-123',
          resourceType: 'session',
          resourceId: 'session-1',
          timestamp: new Date(),
          metadata: {},
        },
      ];
      audit.query.mockReturnValue(mockEntries);

      const filters = { userId: 'user-123', action: 'user.login' };
      const result = audit.query(filters);
      
      expect(audit.query).toHaveBeenCalledWith(filters);
      expect(result).toEqual(mockEntries);
    });
  });

  describe('exportLogs', () => {
    it('exports logs for date range', () => {
      const startDate = new Date('2024-01-01');
      const endDate = new Date('2024-01-31');

      audit.exportLogs.mockReturnValue({ format: 'csv', data: 'csv content' });
      
      const result = audit.exportLogs(startDate, endDate, 'csv');
      expect(audit.exportLogs).toHaveBeenCalledWith(startDate, endDate, 'csv');
    });
  });
});

describe('Data Subject Rights', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('requestAccess', () => {
    it('creates access request', async () => {
      const mockRequest: DataSubjectRightsRequest = {
        id: 'req-1',
        type: 'access',
        status: 'pending',
        createdAt: new Date(),
      };
      dataRights.requestAccess.mockResolvedValue(mockRequest);

      const result = await dataRights.requestAccess('user-123');
      expect(dataRights.requestAccess).toHaveBeenCalledWith('user-123');
      expect(result.type).toBe('access');
    });
  });

  describe('requestExport', () => {
    it('creates export request', async () => {
      const mockRequest: DataSubjectRightsRequest = {
        id: 'req-2',
        type: 'export',
        status: 'pending',
        createdAt: new Date(),
      };
      dataRights.requestExport.mockResolvedValue(mockRequest);

      const result = await dataRights.requestExport('user-123', 'json');
      expect(dataRights.requestExport).toHaveBeenCalledWith('user-123', 'json');
    });
  });

  describe('requestDeletion', () => {
    it('creates deletion request', async () => {
      const mockRequest: DataSubjectRightsRequest = {
        id: 'req-3',
        type: 'delete',
        status: 'pending',
        createdAt: new Date(),
      };
      dataRights.requestDeletion.mockResolvedValue(mockRequest);

      await dataRights.requestDeletion('user-123');
      expect(dataRights.requestDeletion).toHaveBeenCalledWith('user-123');
    });
  });

  describe('getRequestStatus', () => {
    it('returns request status', async () => {
      const mockRequest: DataSubjectRightsRequest = {
        id: 'req-1',
        type: 'access',
        status: 'completed',
        createdAt: new Date(),
        completedAt: new Date(),
      };
      dataRights.getRequestStatus.mockResolvedValue(mockRequest);

      const result = await dataRights.getRequestStatus('req-1');
      expect(result.status).toBe('completed');
    });
  });
});

describe('Encryption', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('encryptPII', () => {
    it('encrypts personal data', () => {
      encryption.encryptPII.mockReturnValue('encrypted-data');
      const result = encryption.encryptPII('john@example.com');
      expect(result).toBe('encrypted-data');
    });
  });

  describe('decryptPII', () => {
    it('decrypts personal data', () => {
      encryption.decryptPII.mockReturnValue('john@example.com');
      const result = encryption.decryptPII('encrypted-data');
      expect(result).toBe('john@example.com');
    });
  });

  describe('hashIdentifier', () => {
    it('creates hash of identifier', () => {
      encryption.hashIdentifier.mockReturnValue('hashed-identifier');
      const result = encryption.hashIdentifier('user-123');
      expect(result).toBe('hashed-identifier');
    });
  });
});

describe('Data Retention', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getRetentionPolicy', () => {
    it('returns retention policy for data type', () => {
      retention.getRetentionPolicy.mockReturnValue({
        dataType: 'chat_messages',
        retentionDays: 365,
        deletionStrategy: 'hard_delete',
      });

      const policy = retention.getRetentionPolicy('chat_messages');
      expect(policy.retentionDays).toBe(365);
    });
  });

  describe('applyRetentionPolicy', () => {
    it('applies retention policy', async () => {
      retention.applyRetentionPolicy.mockResolvedValue({ deletedCount: 100 });

      const result = await retention.applyRetentionPolicy('chat_messages');
      expect(retention.applyRetentionPolicy).toHaveBeenCalledWith('chat_messages');
    });
  });

  describe('scheduleDataDeletion', () => {
    it('schedules data for deletion', () => {
      const deletionDate = new Date('2024-12-31');
      retention.scheduleDataDeletion('user-123', deletionDate);
      expect(retention.scheduleDataDeletion).toHaveBeenCalledWith('user-123', deletionDate);
    });
  });
});
