'use client';

import { useState } from 'react';
import {
  Shield,
  Check,
  X,
  Info,
} from 'lucide-react';

interface Role {
  id: string;
  name: string;
  description: string;
  userCount: number;
  permissions: string[];
}

const PLATFORM_ROLES: Role[] = [
  {
    id: 'staff_admin',
    name: 'Staff Admin',
    description: 'Full platform access including system configuration',
    userCount: 0,
    permissions: [
      'admin.access',
      'admin.users.manage',
      'admin.orgs.manage',
      'admin.settings.manage',
      'admin.analytics.view',
      'admin.trials.manage',
      'admin.billing.manage',
    ],
  },
  {
    id: 'org_admin',
    name: 'Organization Admin',
    description: 'Full access within their organization',
    userCount: 0,
    permissions: [
      'org.settings.manage',
      'org.members.manage',
      'org.billing.manage',
      'org.integrations.manage',
      'org.agents.manage',
      'org.documents.manage',
      'org.analytics.view',
      'org.audit.view',
    ],
  },
  {
    id: 'member',
    name: 'Member',
    description: 'Standard access to organization resources',
    userCount: 0,
    permissions: [
      'chat.use',
      'agents.use',
      'documents.upload',
      'documents.view',
      'analytics.view',
    ],
  },
  {
    id: 'viewer',
    name: 'Viewer',
    description: 'Read-only access to organization resources',
    userCount: 0,
    permissions: [
      'chat.view',
      'documents.view',
      'analytics.view',
    ],
  },
];

const ALL_PERMISSIONS = [
  { category: 'Admin', perms: ['admin.access', 'admin.users.manage', 'admin.orgs.manage', 'admin.settings.manage', 'admin.analytics.view', 'admin.trials.manage', 'admin.billing.manage'] },
  { category: 'Organization', perms: ['org.settings.manage', 'org.members.manage', 'org.billing.manage', 'org.integrations.manage', 'org.agents.manage', 'org.documents.manage', 'org.analytics.view', 'org.audit.view'] },
  { category: 'Features', perms: ['chat.use', 'chat.view', 'agents.use', 'documents.upload', 'documents.view', 'analytics.view'] },
];

export default function AdminRolesPage() {
  const [selectedRole, setSelectedRole] = useState<string>('staff_admin');

  const currentRole = PLATFORM_ROLES.find((r) => r.id === selectedRole);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Roles & Permissions</h1>
        <p className="text-muted-foreground mt-1">
          View and manage platform role definitions
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-2">
          {PLATFORM_ROLES.map((role) => (
            <button
              key={role.id}
              onClick={() => setSelectedRole(role.id)}
              className={`w-full text-left rounded-xl border p-4 transition-colors ${
                selectedRole === role.id
                  ? 'border-primary bg-primary/5'
                  : 'hover:bg-muted/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <Shield
                  className={`h-5 w-5 ${
                    selectedRole === role.id
                      ? 'text-primary'
                      : 'text-muted-foreground'
                  }`}
                />
                <div>
                  <p className="font-medium">{role.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {role.description}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="lg:col-span-2 rounded-xl border bg-card">
          <div className="p-6 border-b">
            <h2 className="text-lg font-semibold">
              {currentRole?.name} Permissions
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {currentRole?.permissions.length} permissions granted
            </p>
          </div>
          <div className="p-6 space-y-6">
            {ALL_PERMISSIONS.map((group) => (
              <div key={group.category}>
                <h3 className="text-sm font-medium text-muted-foreground mb-3">
                  {group.category}
                </h3>
                <div className="space-y-2">
                  {group.perms.map((perm) => {
                    const hasPermission =
                      currentRole?.permissions.includes(perm) ?? false;
                    return (
                      <div
                        key={perm}
                        className="flex items-center justify-between py-1.5"
                      >
                        <span className="text-sm font-mono">{perm}</span>
                        {hasPermission ? (
                          <Check className="h-4 w-4 text-green-500" />
                        ) : (
                          <X className="h-4 w-4 text-muted-foreground/40" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

            <div className="flex items-start gap-2 rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">
              <Info className="h-4 w-4 mt-0.5 shrink-0" />
              <p>
                Role definitions are managed at the platform level. Contact a
                staff admin to modify role permissions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
