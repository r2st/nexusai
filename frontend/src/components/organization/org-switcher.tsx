'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  Building2,
  ChevronDown,
  Check,
  Plus,
  Settings,
  Users,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { organizationsApi, type Organization, TenantContext } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

interface OrgSwitcherProps {
  className?: string;
  compact?: boolean;
}

export function OrgSwitcher({ className, compact = false }: OrgSwitcherProps) {
  const { isAuthenticated } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [currentOrg, setCurrentOrg] = useState<Organization | null>(null);

  const loadOrganizations = useCallback(async () => {
    if (!isAuthenticated) return;

    setIsLoading(true);
    try {
      const orgs = await organizationsApi.list();
      setOrganizations(orgs);

      // Get current org from context
      const currentOrgId = TenantContext.getCurrentTenantId();
      if (currentOrgId) {
        const current = orgs.find((o) => o.id === currentOrgId);
        setCurrentOrg(current || null);
      } else if (orgs.length > 0) {
        // Auto-select first org if none selected
        setCurrentOrg(orgs[0]);
        TenantContext.setCurrentTenantId(orgs[0].id);
      }
    } catch (error) {
      console.error('Failed to load organizations:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    loadOrganizations();
  }, [loadOrganizations]);

  // Listen for tenant context changes
  useEffect(() => {
    const unsubscribe = TenantContext.subscribe((tenantId) => {
      if (tenantId) {
        const org = organizations.find((o) => o.id === tenantId);
        setCurrentOrg(org || null);
      } else {
        setCurrentOrg(null);
      }
    });

    return unsubscribe;
  }, [organizations]);

  const handleSelectOrg = (org: Organization) => {
    setCurrentOrg(org);
    TenantContext.setCurrentTenantId(org.id);
    setIsOpen(false);
    // Refresh page data with new tenant context
    window.location.reload();
  };

  if (!isAuthenticated) {
    return null;
  }

  if (isLoading) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        {!compact && <span className="text-sm text-muted-foreground">Loading...</span>}
      </div>
    );
  }

  if (organizations.length === 0) {
    return (
      <Link href="/onboarding">
        <Button variant="outline" size="sm" className={className}>
          <Plus className="mr-2 h-4 w-4" />
          Create Organization
        </Button>
      </Link>
    );
  }

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={currentOrg ? `Organization: ${currentOrg.name}` : 'Select organization'}
        className={cn(
          'flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm font-medium transition-colors hover:bg-muted',
          compact ? 'w-auto' : 'w-full'
        )}
      >
        <div className="flex h-6 w-6 items-center justify-center rounded bg-primary/10">
          <Building2 className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
        </div>
        {!compact && (
          <>
            <span className="flex-1 text-left truncate">
              {currentOrg?.name || 'Select Organization'}
            </span>
            <ChevronDown
              className={cn(
                'h-4 w-4 text-muted-foreground transition-transform',
                isOpen && 'rotate-180'
              )}
            />
          </>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />

          {/* Menu */}
          <div role="listbox" aria-label="Organizations" className="absolute left-0 top-full mt-2 z-50 w-72 rounded-lg border bg-popover shadow-lg">
            <div className="p-2">
              <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                Organizations
              </p>

              <div className="space-y-1">
                {organizations.map((org) => (
                  <button
                    key={org.id}
                    role="option"
                    aria-selected={currentOrg?.id === org.id}
                    onClick={() => handleSelectOrg(org)}
                    className={cn(
                      'w-full flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors',
                      currentOrg?.id === org.id
                        ? 'bg-primary/10 text-primary'
                        : 'hover:bg-muted'
                    )}
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/10">
                      <Building2 className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 text-left min-w-0">
                      <p className="font-medium truncate">{org.name}</p>
                      <p className="text-xs text-muted-foreground capitalize">
                        {org.tier} plan
                      </p>
                    </div>
                    {currentOrg?.id === org.id && (
                      <Check className="h-4 w-4 text-primary shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            </div>

            <hr />

            <div className="p-2">
              <Link
                href="/team"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-muted transition-colors"
              >
                <Users className="h-4 w-4" />
                Manage Team
              </Link>
              <Link
                href="/settings"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-muted transition-colors"
              >
                <Settings className="h-4 w-4" />
                Organization Settings
              </Link>
            </div>

            <hr />

            <div className="p-2">
              <Link
                href="/onboarding?mode=create-org"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-muted transition-colors"
              >
                <Plus className="h-4 w-4" />
                Create New Organization
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/**
 * Compact version for use in headers/sidebars
 */
export function OrgSwitcherCompact({ className }: { className?: string }) {
  return <OrgSwitcher className={className} compact />;
}
