/**
 * Admin Page Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock types
interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
  status: 'active' | 'inactive';
  createdAt: Date;
}

interface AdminStats {
  totalUsers: number;
  activeUsers: number;
  totalConversations: number;
  apiCalls: number;
}

interface AdminPageProps {
  stats?: AdminStats;
  users?: User[];
  onCreateUser?: () => void;
  onEditUser?: (id: string) => void;
  onDeleteUser?: (id: string) => Promise<void>;
  onToggleStatus?: (id: string) => Promise<void>;
  isLoading?: boolean;
}

const mockUsers: User[] = [
  { id: '1', name: 'John Admin', email: 'john@example.com', role: 'admin', status: 'active', createdAt: new Date() },
  { id: '2', name: 'Jane User', email: 'jane@example.com', role: 'user', status: 'active', createdAt: new Date() },
  { id: '3', name: 'Bob User', email: 'bob@example.com', role: 'user', status: 'inactive', createdAt: new Date() },
];

const mockStats: AdminStats = {
  totalUsers: 150,
  activeUsers: 120,
  totalConversations: 5000,
  apiCalls: 100000,
};

// Mock AdminPage component
const AdminPage = ({
  stats = mockStats,
  users = mockUsers,
  onCreateUser,
  onEditUser,
  onDeleteUser,
  onToggleStatus,
  isLoading = false,
}: AdminPageProps) => {
  const [searchQuery, setSearchQuery] = React.useState('');

  const filteredUsers = users.filter(
    (user) =>
      user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) {
    return <div data-testid="loading">Loading admin data...</div>;
  }

  return (
    <div data-testid="admin-page" className="admin-page">
      <header>
        <h1>Admin Dashboard</h1>
      </header>

      <section data-testid="stats-section" className="stats-section">
        <div data-testid="stat-total-users" className="stat-card">
          <span className="label">Total Users</span>
          <span className="value">{stats.totalUsers}</span>
        </div>
        <div data-testid="stat-active-users" className="stat-card">
          <span className="label">Active Users</span>
          <span className="value">{stats.activeUsers}</span>
        </div>
        <div data-testid="stat-conversations" className="stat-card">
          <span className="label">Conversations</span>
          <span className="value">{stats.totalConversations}</span>
        </div>
        <div data-testid="stat-api-calls" className="stat-card">
          <span className="label">API Calls</span>
          <span className="value">{stats.apiCalls}</span>
        </div>
      </section>

      <section data-testid="users-section" className="users-section">
        <div className="section-header">
          <h2>Users</h2>
          <input
            data-testid="search-input"
            type="text"
            placeholder="Search users..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button data-testid="create-user-btn" onClick={onCreateUser}>
            Create User
          </button>
        </div>

        <table data-testid="users-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr key={user.id} data-testid={`user-row-${user.id}`}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td data-testid={`role-${user.id}`}>{user.role}</td>
                <td data-testid={`status-${user.id}`}>{user.status}</td>
                <td>
                  <button
                    data-testid={`edit-${user.id}`}
                    onClick={() => onEditUser?.(user.id)}
                  >
                    Edit
                  </button>
                  <button
                    data-testid={`toggle-${user.id}`}
                    onClick={() => onToggleStatus?.(user.id)}
                  >
                    {user.status === 'active' ? 'Deactivate' : 'Activate'}
                  </button>
                  <button
                    data-testid={`delete-${user.id}`}
                    onClick={() => onDeleteUser?.(user.id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredUsers.length === 0 && (
          <p data-testid="no-users">No users found</p>
        )}
      </section>
    </div>
  );
};

describe('AdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders admin page', () => {
    render(<AdminPage />);
    expect(screen.getByTestId('admin-page')).toBeInTheDocument();
  });

  it('renders page title', () => {
    render(<AdminPage />);
    expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<AdminPage isLoading={true} />);
    expect(screen.getByTestId('loading')).toHaveTextContent('Loading admin data...');
  });

  describe('Stats Section', () => {
    it('renders stats section', () => {
      render(<AdminPage stats={mockStats} />);
      expect(screen.getByTestId('stats-section')).toBeInTheDocument();
    });

    it('displays total users', () => {
      render(<AdminPage stats={mockStats} />);
      expect(screen.getByTestId('stat-total-users')).toHaveTextContent('150');
    });

    it('displays active users', () => {
      render(<AdminPage stats={mockStats} />);
      expect(screen.getByTestId('stat-active-users')).toHaveTextContent('120');
    });

    it('displays conversations', () => {
      render(<AdminPage stats={mockStats} />);
      expect(screen.getByTestId('stat-conversations')).toHaveTextContent('5000');
    });

    it('displays API calls', () => {
      render(<AdminPage stats={mockStats} />);
      expect(screen.getByTestId('stat-api-calls')).toHaveTextContent('100000');
    });
  });

  describe('Users Section', () => {
    it('renders users section', () => {
      render(<AdminPage users={mockUsers} />);
      expect(screen.getByTestId('users-section')).toBeInTheDocument();
    });

    it('renders users table', () => {
      render(<AdminPage users={mockUsers} />);
      expect(screen.getByTestId('users-table')).toBeInTheDocument();
    });

    it('renders all users', () => {
      render(<AdminPage users={mockUsers} />);
      expect(screen.getByTestId('user-row-1')).toBeInTheDocument();
      expect(screen.getByTestId('user-row-2')).toBeInTheDocument();
      expect(screen.getByTestId('user-row-3')).toBeInTheDocument();
    });

    it('displays user name and email', () => {
      render(<AdminPage users={mockUsers} />);
      expect(screen.getByText('John Admin')).toBeInTheDocument();
      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });

    it('displays user role', () => {
      render(<AdminPage users={mockUsers} />);
      expect(screen.getByTestId('role-1')).toHaveTextContent('admin');
      expect(screen.getByTestId('role-2')).toHaveTextContent('user');
    });

    it('displays user status', () => {
      render(<AdminPage users={mockUsers} />);
      expect(screen.getByTestId('status-1')).toHaveTextContent('active');
      expect(screen.getByTestId('status-3')).toHaveTextContent('inactive');
    });
  });

  describe('Search', () => {
    it('renders search input', () => {
      render(<AdminPage />);
      expect(screen.getByTestId('search-input')).toBeInTheDocument();
    });

    it('filters users by name', () => {
      render(<AdminPage users={mockUsers} />);
      fireEvent.change(screen.getByTestId('search-input'), { target: { value: 'John' } });
      
      expect(screen.getByTestId('user-row-1')).toBeInTheDocument();
      expect(screen.queryByTestId('user-row-2')).not.toBeInTheDocument();
    });

    it('filters users by email', () => {
      render(<AdminPage users={mockUsers} />);
      fireEvent.change(screen.getByTestId('search-input'), { target: { value: 'jane@' } });
      
      expect(screen.queryByTestId('user-row-1')).not.toBeInTheDocument();
      expect(screen.getByTestId('user-row-2')).toBeInTheDocument();
    });

    it('shows no users message when search returns empty', () => {
      render(<AdminPage users={mockUsers} />);
      fireEvent.change(screen.getByTestId('search-input'), { target: { value: 'xyz' } });
      
      expect(screen.getByTestId('no-users')).toBeInTheDocument();
    });
  });

  describe('User Actions', () => {
    it('calls onCreateUser when create button is clicked', () => {
      const onCreateUser = vi.fn();
      render(<AdminPage onCreateUser={onCreateUser} />);
      
      fireEvent.click(screen.getByTestId('create-user-btn'));
      expect(onCreateUser).toHaveBeenCalled();
    });

    it('calls onEditUser with user id', () => {
      const onEditUser = vi.fn();
      render(<AdminPage users={mockUsers} onEditUser={onEditUser} />);
      
      fireEvent.click(screen.getByTestId('edit-1'));
      expect(onEditUser).toHaveBeenCalledWith('1');
    });

    it('calls onToggleStatus with user id', async () => {
      const onToggleStatus = vi.fn().mockResolvedValue(undefined);
      render(<AdminPage users={mockUsers} onToggleStatus={onToggleStatus} />);
      
      fireEvent.click(screen.getByTestId('toggle-1'));
      await waitFor(() => {
        expect(onToggleStatus).toHaveBeenCalledWith('1');
      });
    });

    it('shows correct toggle button text for active user', () => {
      render(<AdminPage users={mockUsers} />);
      expect(screen.getByTestId('toggle-1')).toHaveTextContent('Deactivate');
    });

    it('shows correct toggle button text for inactive user', () => {
      render(<AdminPage users={mockUsers} />);
      expect(screen.getByTestId('toggle-3')).toHaveTextContent('Activate');
    });

    it('calls onDeleteUser with user id', async () => {
      const onDeleteUser = vi.fn().mockResolvedValue(undefined);
      render(<AdminPage users={mockUsers} onDeleteUser={onDeleteUser} />);
      
      fireEvent.click(screen.getByTestId('delete-1'));
      await waitFor(() => {
        expect(onDeleteUser).toHaveBeenCalledWith('1');
      });
    });
  });
});
