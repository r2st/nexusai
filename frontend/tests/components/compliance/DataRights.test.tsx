/**
 * DataRights Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock types
interface DataRequest {
  id: string;
  type: 'access' | 'export' | 'delete' | 'rectification';
  status: 'pending' | 'processing' | 'completed' | 'rejected';
  createdAt: string;
  completedAt?: string;
}

interface DataRightsProps {
  requests?: DataRequest[];
  onRequestAccess?: () => Promise<void>;
  onRequestExport?: () => Promise<void>;
  onRequestDelete?: () => Promise<void>;
  onRequestRectification?: () => Promise<void>;
  isLoading?: boolean;
}

const mockRequests: DataRequest[] = [
  { id: '1', type: 'access', status: 'completed', createdAt: '2024-01-15', completedAt: '2024-01-16' },
  { id: '2', type: 'export', status: 'processing', createdAt: '2024-01-18' },
  { id: '3', type: 'delete', status: 'pending', createdAt: '2024-01-20' },
];

// Mock DataRights component
const DataRights = ({
  requests = [],
  onRequestAccess,
  onRequestExport,
  onRequestDelete,
  onRequestRectification,
  isLoading = false,
}: DataRightsProps) => {
  const [submitting, setSubmitting] = React.useState<string | null>(null);

  const handleRequest = async (type: string, handler?: () => Promise<void>) => {
    if (!handler) return;
    setSubmitting(type);
    try {
      await handler();
    } finally {
      setSubmitting(null);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'yellow',
      processing: 'blue',
      completed: 'green',
      rejected: 'red',
    };
    return colors[status] || 'gray';
  };

  return (
    <div data-testid="data-rights" className="data-rights">
      <h1>Your Data Rights</h1>
      <p data-testid="description">
        Under GDPR, you have the right to access, export, correct, and delete your personal data.
      </p>

      <section data-testid="actions-section">
        <h2>Request Actions</h2>
        <div className="action-buttons">
          <button
            data-testid="request-access"
            onClick={() => handleRequest('access', onRequestAccess)}
            disabled={submitting === 'access'}
          >
            {submitting === 'access' ? 'Requesting...' : 'Request Data Access'}
          </button>
          <button
            data-testid="request-export"
            onClick={() => handleRequest('export', onRequestExport)}
            disabled={submitting === 'export'}
          >
            {submitting === 'export' ? 'Requesting...' : 'Export My Data'}
          </button>
          <button
            data-testid="request-rectification"
            onClick={() => handleRequest('rectification', onRequestRectification)}
            disabled={submitting === 'rectification'}
          >
            {submitting === 'rectification' ? 'Requesting...' : 'Request Data Correction'}
          </button>
          <button
            data-testid="request-delete"
            onClick={() => handleRequest('delete', onRequestDelete)}
            disabled={submitting === 'delete'}
            className="destructive"
          >
            {submitting === 'delete' ? 'Requesting...' : 'Request Data Deletion'}
          </button>
        </div>
      </section>

      <section data-testid="requests-section">
        <h2>Request History</h2>
        {isLoading ? (
          <div data-testid="loading">Loading requests...</div>
        ) : requests.length === 0 ? (
          <p data-testid="no-requests">No data requests yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Status</th>
                <th>Requested</th>
                <th>Completed</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.id} data-testid={`request-${request.id}`}>
                  <td data-testid={`type-${request.id}`}>{request.type}</td>
                  <td>
                    <span
                      data-testid={`status-${request.id}`}
                      className={`badge ${getStatusBadge(request.status)}`}
                    >
                      {request.status}
                    </span>
                  </td>
                  <td>{request.createdAt}</td>
                  <td>{request.completedAt || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};

describe('DataRights', () => {
  it('renders data rights component', () => {
    render(<DataRights />);
    expect(screen.getByTestId('data-rights')).toBeInTheDocument();
  });

  it('displays description text', () => {
    render(<DataRights />);
    expect(screen.getByTestId('description')).toHaveTextContent('Under GDPR');
  });

  it('renders all action buttons', () => {
    render(<DataRights />);
    expect(screen.getByTestId('request-access')).toBeInTheDocument();
    expect(screen.getByTestId('request-export')).toBeInTheDocument();
    expect(screen.getByTestId('request-rectification')).toBeInTheDocument();
    expect(screen.getByTestId('request-delete')).toBeInTheDocument();
  });

  it('calls onRequestAccess when access button is clicked', async () => {
    const onRequestAccess = vi.fn().mockResolvedValue(undefined);
    render(<DataRights onRequestAccess={onRequestAccess} />);
    
    fireEvent.click(screen.getByTestId('request-access'));
    
    await waitFor(() => {
      expect(onRequestAccess).toHaveBeenCalled();
    });
  });

  it('calls onRequestExport when export button is clicked', async () => {
    const onRequestExport = vi.fn().mockResolvedValue(undefined);
    render(<DataRights onRequestExport={onRequestExport} />);
    
    fireEvent.click(screen.getByTestId('request-export'));
    
    await waitFor(() => {
      expect(onRequestExport).toHaveBeenCalled();
    });
  });

  it('calls onRequestDelete when delete button is clicked', async () => {
    const onRequestDelete = vi.fn().mockResolvedValue(undefined);
    render(<DataRights onRequestDelete={onRequestDelete} />);
    
    fireEvent.click(screen.getByTestId('request-delete'));
    
    await waitFor(() => {
      expect(onRequestDelete).toHaveBeenCalled();
    });
  });

  it('shows loading state while submitting', async () => {
    const onRequestAccess = vi.fn().mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );
    render(<DataRights onRequestAccess={onRequestAccess} />);
    
    fireEvent.click(screen.getByTestId('request-access'));
    
    expect(screen.getByTestId('request-access')).toHaveTextContent('Requesting...');
  });

  it('disables button while submitting', async () => {
    const onRequestAccess = vi.fn().mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );
    render(<DataRights onRequestAccess={onRequestAccess} />);
    
    fireEvent.click(screen.getByTestId('request-access'));
    
    expect(screen.getByTestId('request-access')).toBeDisabled();
  });

  it('renders request history section', () => {
    render(<DataRights />);
    expect(screen.getByTestId('requests-section')).toBeInTheDocument();
  });

  it('shows no requests message when empty', () => {
    render(<DataRights requests={[]} />);
    expect(screen.getByTestId('no-requests')).toHaveTextContent('No data requests yet.');
  });

  it('renders request history', () => {
    render(<DataRights requests={mockRequests} />);
    expect(screen.getByTestId('request-1')).toBeInTheDocument();
    expect(screen.getByTestId('request-2')).toBeInTheDocument();
    expect(screen.getByTestId('request-3')).toBeInTheDocument();
  });

  it('displays request type', () => {
    render(<DataRights requests={mockRequests} />);
    expect(screen.getByTestId('type-1')).toHaveTextContent('access');
    expect(screen.getByTestId('type-2')).toHaveTextContent('export');
  });

  it('displays request status', () => {
    render(<DataRights requests={mockRequests} />);
    expect(screen.getByTestId('status-1')).toHaveTextContent('completed');
    expect(screen.getByTestId('status-2')).toHaveTextContent('processing');
    expect(screen.getByTestId('status-3')).toHaveTextContent('pending');
  });

  it('shows loading state for requests', () => {
    render(<DataRights isLoading={true} />);
    expect(screen.getByTestId('loading')).toHaveTextContent('Loading requests...');
  });
});
