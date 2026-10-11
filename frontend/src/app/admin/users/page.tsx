'use client';

/**
 * Admin Users Page
 *
 * List and manage all users in the system with search, filter, and CRUD operations.
 */

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Users,
  Search,
  Filter,
  Plus,
  MoreVertical,
  Edit,
  Trash2,
  Shield,
  CheckCircle,
  XCircle,
  Mail,
  ChevronLeft,
  ChevronRight,
  Download,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api, User } from '@/lib/api';
import { toast } from 'sonner';

// Extended user type for admin
interface AdminUser extends User {
  created_at: string;
  last_login_at: string | null;
  organization_count: number;
  is_active: boolean;
}

type UserFilter = 'all' | 'active' | 'inactive' | 'verified' | 'unverified' | 'admin';

function AdminUsersLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

export default function AdminUsersPage() {
  return (
    <Suspense fallback={<AdminUsersLoading />}>
      <AdminUsersContent />
    </Suspense>
  );
}

function AdminUsersContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<UserFilter>((searchParams.get('filter') as UserFilter) || 'all');
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  });
  const [isActionMenuOpen, setIsActionMenuOpen] = useState<string | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<AdminUser | null>(null);

  // Fetch users
  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      // In production, this would be an actual API call with filters
      // const response = await api.get('/admin/users', {
      //   params: { search: searchQuery, filter, page: pagination.page, limit: pagination.limit }
      // });

      // Mock data for now
      const mockUsers: AdminUser[] = [
        {
          id: '1',
          email: 'admin@nexusai.com',
          username: 'admin',
          full_name: 'System Admin',
          role: 'admin',
          is_verified: true,
          created_at: '2024-01-01T00:00:00Z',
          last_login_at: new Date().toISOString(),
          organization_count: 3,
          is_active: true,
        },
        {
          id: '2',
          email: 'john@example.com',
          username: 'johndoe',
          full_name: 'John Doe',
          role: 'user',
          is_verified: true,
          created_at: '2024-06-15T00:00:00Z',
          last_login_at: new Date(Date.now() - 86400000).toISOString(),
          organization_count: 2,
          is_active: true,
        },
        {
          id: '3',
          email: 'jane@example.com',
          username: 'janesmith',
          full_name: 'Jane Smith',
          role: 'user',
          is_verified: false,
          created_at: '2024-12-01T00:00:00Z',
          last_login_at: null,
          organization_count: 1,
          is_active: true,
        },
        {
          id: '4',
          email: 'mike@company.com',
          username: 'mikedev',
          full_name: 'Mike Developer',
          role: 'user',
          is_verified: true,
          created_at: '2024-11-20T00:00:00Z',
          last_login_at: new Date(Date.now() - 172800000).toISOString(),
          organization_count: 1,
          is_active: false,
        },
        {
          id: '5',
          email: 'sarah@startup.io',
          username: 'sarahcto',
          full_name: 'Sarah Johnson',
          role: 'admin',
          is_verified: true,
          created_at: '2024-09-10T00:00:00Z',
          last_login_at: new Date(Date.now() - 3600000).toISOString(),
          organization_count: 5,
          is_active: true,
        },
      ];

      // Apply filters
      let filteredUsers = mockUsers;

      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filteredUsers = filteredUsers.filter(
          (user) =>
            user.email.toLowerCase().includes(query) ||
            user.username.toLowerCase().includes(query) ||
            (user.full_name && user.full_name.toLowerCase().includes(query))
        );
      }

      switch (filter) {
        case 'active':
          filteredUsers = filteredUsers.filter((u) => u.is_active);
          break;
        case 'inactive':
          filteredUsers = filteredUsers.filter((u) => !u.is_active);
          break;
        case 'verified':
          filteredUsers = filteredUsers.filter((u) => u.is_verified);
          break;
        case 'unverified':
          filteredUsers = filteredUsers.filter((u) => !u.is_verified);
          break;
        case 'admin':
          filteredUsers = filteredUsers.filter((u) => u.role === 'admin');
          break;
      }

      setUsers(filteredUsers);
      setPagination((prev) => ({
        ...prev,
        total: filteredUsers.length,
        totalPages: Math.ceil(filteredUsers.length / prev.limit),
      }));
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, filter, pagination.page, pagination.limit]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleSelectAll = () => {
    if (selectedUsers.size === users.length) {
      setSelectedUsers(new Set());
    } else {
      setSelectedUsers(new Set(users.map((u) => u.id)));
    }
  };

  const handleSelectUser = (userId: string) => {
    const newSelected = new Set(selectedUsers);
    if (newSelected.has(userId)) {
      newSelected.delete(userId);
    } else {
      newSelected.add(userId);
    }
    setSelectedUsers(newSelected);
  };

  const handleDeleteUser = async (user: AdminUser) => {
    setUserToDelete(user);
    setIsDeleteModalOpen(true);
    setIsActionMenuOpen(null);
  };

  const confirmDelete = async () => {
    if (!userToDelete) return;

    try {
      // await api.delete(`/admin/users/${userToDelete.id}`);
      setUsers((prev) => prev.filter((u) => u.id !== userToDelete.id));
      setIsDeleteModalOpen(false);
      setUserToDelete(null);
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  const handleToggleActive = async (user: AdminUser) => {
    try {
      // await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active });
      setUsers((prev) =>
        prev.map((u) => (u.id === user.id ? { ...u, is_active: !u.is_active } : u))
      );
    } catch (error) {
      console.error('Failed to toggle user status:', error);
    }
    setIsActionMenuOpen(null);
  };

  const handleResendVerification = async (user: AdminUser) => {
    try {
      // await api.post(`/admin/users/${user.id}/resend-verification`);
      toast.success('Verification email sent');
    } catch (error) {
      console.error('Failed to resend verification:', error);
    }
    setIsActionMenuOpen(null);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const filterOptions: { value: UserFilter; label: string }[] = [
    { value: 'all', label: 'All Users' },
    { value: 'active', label: 'Active' },
    { value: 'inactive', label: 'Inactive' },
    { value: 'verified', label: 'Verified' },
    { value: 'unverified', label: 'Unverified' },
    { value: 'admin', label: 'Admins' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Users</h1>
          <p className="text-muted-foreground">Manage user accounts and permissions</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchUsers}
            className="inline-flex items-center gap-2 px-3 py-2 border rounded-lg hover:bg-muted transition-colors"
            aria-label="Refresh users"
          >
            <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} aria-hidden="true" />
          </button>
          <button className="inline-flex items-center gap-2 px-3 py-2 border rounded-lg hover:bg-muted transition-colors">
            <Download className="h-4 w-4" aria-hidden="true" />
            Export
          </button>
          <Link
            href="/admin/users/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add User
          </Link>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search by name, email, or username..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            aria-label="Search users"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as UserFilter)}
            className="px-3 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            aria-label="Filter users"
          >
            {filterOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedUsers.size > 0 && (
        <div className="flex items-center gap-4 p-3 bg-muted rounded-lg">
          <span className="text-sm font-medium">{selectedUsers.size} selected</span>
          <button className="text-sm text-primary hover:underline">Activate</button>
          <button className="text-sm text-primary hover:underline">Deactivate</button>
          <button className="text-sm text-destructive hover:underline">Delete</button>
        </div>
      )}

      {/* Users Table */}
      <div className="border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="w-12 px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedUsers.size === users.length && users.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                    aria-label="Select all users"
                  />
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium">User</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Role</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Organizations</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Last Login</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Created</th>
                <th className="w-12 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b">
                    <td colSpan={8} className="px-4 py-4">
                      <div className="h-10 bg-muted rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-muted-foreground">
                    <Users className="h-12 w-12 mx-auto mb-4 opacity-20" />
                    <p>No users found</p>
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="border-b hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedUsers.has(user.id)}
                        onChange={() => handleSelectUser(user.id)}
                        className="rounded border-gray-300"
                        aria-label={`Select ${user.full_name || user.username || user.email}`}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/users/${user.id}`}
                        className="flex items-center gap-3 hover:opacity-80"
                      >
                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-sm font-medium text-primary">
                            {(user.full_name || user.username).charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <div className="font-medium">{user.full_name || user.username}</div>
                          <div className="text-sm text-muted-foreground">{user.email}</div>
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                          user.role === 'admin'
                            ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                        )}
                      >
                        {user.role === 'admin' && <Shield className="h-3 w-3" />}
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                            user.is_active
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          )}
                        >
                          {user.is_active ? (
                            <>
                              <CheckCircle className="h-3 w-3" />
                              Active
                            </>
                          ) : (
                            <>
                              <XCircle className="h-3 w-3" />
                              Inactive
                            </>
                          )}
                        </span>
                        {!user.is_verified && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                            Unverified
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {user.organization_count}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatDate(user.last_login_at)}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="relative">
                        <button
                          onClick={() =>
                            setIsActionMenuOpen(isActionMenuOpen === user.id ? null : user.id)
                          }
                          className="p-1 hover:bg-muted rounded transition-colors"
                          aria-label={`Actions for ${user.full_name || user.username || user.email}`}
                        >
                          <MoreVertical className="h-4 w-4" aria-hidden="true" />
                        </button>
                        {isActionMenuOpen === user.id && (
                          <>
                            <div
                              className="fixed inset-0 z-10"
                              onClick={() => setIsActionMenuOpen(null)}
                            />
                            <div className="absolute right-0 top-8 z-20 w-48 bg-background border rounded-lg shadow-lg py-1">
                              <Link
                                href={`/admin/users/${user.id}`}
                                className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted"
                                onClick={() => setIsActionMenuOpen(null)}
                              >
                                <Edit className="h-4 w-4" />
                                Edit User
                              </Link>
                              <button
                                onClick={() => handleToggleActive(user)}
                                className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted w-full text-left"
                              >
                                {user.is_active ? (
                                  <>
                                    <XCircle className="h-4 w-4" />
                                    Deactivate
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle className="h-4 w-4" />
                                    Activate
                                  </>
                                )}
                              </button>
                              {!user.is_verified && (
                                <button
                                  onClick={() => handleResendVerification(user)}
                                  className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted w-full text-left"
                                >
                                  <Mail className="h-4 w-4" />
                                  Resend Verification
                                </button>
                              )}
                              <hr className="my-1" />
                              <button
                                onClick={() => handleDeleteUser(user)}
                                className="flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted w-full text-left text-destructive"
                              >
                                <Trash2 className="h-4 w-4" />
                                Delete User
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {pagination.totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t bg-muted/30">
            <div className="text-sm text-muted-foreground">
              Showing {(pagination.page - 1) * pagination.limit + 1} to{' '}
              {Math.min(pagination.page * pagination.limit, pagination.total)} of {pagination.total}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPagination((p) => ({ ...p, page: p.page - 1 }))}
                disabled={pagination.page === 1}
                className="p-2 border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              </button>
              <span className="text-sm">
                Page {pagination.page} of {pagination.totalPages}
              </span>
              <button
                onClick={() => setPagination((p) => ({ ...p, page: p.page + 1 }))}
                disabled={pagination.page === pagination.totalPages}
                className="p-2 border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && userToDelete && (
        <div role="dialog" aria-modal="true" aria-labelledby="delete-user-title">
          <div
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setIsDeleteModalOpen(false)}
            aria-hidden="true"
          />
          <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-background rounded-lg shadow-lg p-6">
            <h3 id="delete-user-title" className="text-lg font-semibold mb-2">Delete User</h3>
            <p className="text-muted-foreground mb-4">
              Are you sure you want to delete{' '}
              <strong>{userToDelete.full_name || userToDelete.username}</strong>? This action cannot
              be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsDeleteModalOpen(false)}
                className="px-4 py-2 border rounded-lg hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
