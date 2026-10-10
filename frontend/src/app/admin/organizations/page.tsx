'use client';

import { useState, useEffect } from 'react';
import {
  Building2,
  Search,
  Loader2,
  Users,
  Calendar,
  MoreVertical,
  ExternalLink,
} from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { formatRelativeTime } from '@/lib/utils';

interface Organization {
  id: string;
  name: string;
  slug: string;
  owner_email: string;
  member_count: number;
  tier: string;
  created_at: string;
  is_active: boolean;
}

export default function AdminOrganizationsPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadOrganizations();
  }, []);

  const loadOrganizations = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/admin/organizations');
      setOrganizations(response.data);
    } catch {
      toast.error('Failed to load organizations');
    } finally {
      setIsLoading(false);
    }
  };

  const filteredOrgs = organizations.filter(
    (org) =>
      org.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      org.slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
      org.owner_email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTierBadge = (tier: string) => {
    const styles: Record<string, string> = {
      free: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
      pro: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
      enterprise: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
      trial: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    };
    return styles[tier.toLowerCase()] || styles.free;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Organizations</h1>
          <p className="text-muted-foreground mt-1">
            Manage all organizations on the platform
          </p>
        </div>
      </div>

      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by name, slug, or owner email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border bg-background pl-9 pr-3 py-2 text-sm"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredOrgs.length === 0 ? (
        <div className="text-center py-20">
          <Building2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">No organizations found</h3>
          <p className="text-muted-foreground">
            {searchQuery
              ? 'Try adjusting your search query'
              : 'No organizations have been created yet'}
          </p>
        </div>
      ) : (
        <div className="rounded-xl border bg-card">
          <table className="w-full">
            <thead>
              <tr className="border-b text-left text-sm text-muted-foreground">
                <th className="px-4 py-3 font-medium">Organization</th>
                <th className="px-4 py-3 font-medium">Owner</th>
                <th className="px-4 py-3 font-medium">Members</th>
                <th className="px-4 py-3 font-medium">Tier</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrgs.map((org) => (
                <tr key={org.id} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium">{org.name}</p>
                      <p className="text-sm text-muted-foreground">{org.slug}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm">{org.owner_email}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 text-sm">
                      <Users className="h-3.5 w-3.5 text-muted-foreground" />
                      {org.member_count}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getTierBadge(org.tier)}`}
                    >
                      {org.tier}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {formatRelativeTime(org.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        org.is_active
                          ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                          : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                      }`}
                    >
                      {org.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
