'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Users,
  UserPlus,
  Settings,
  Crown,
  Shield,
  User,
  MoreVertical,
  Mail,
  Trash2,
  RefreshCw,
  Loader2,
  Check,
  X,
  Building2,
  Copy,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  organizationsApi,
  type Organization,
  type OrganizationMember,
} from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { FloatingAssistant } from '@/components/assistant';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

type MemberRole = 'owner' | 'admin' | 'member';

const getRoleIcon = (role: MemberRole) => {
  switch (role) {
    case 'owner':
      return <Crown className="h-4 w-4 text-yellow-500" />;
    case 'admin':
      return <Shield className="h-4 w-4 text-blue-500" />;
    default:
      return <User className="h-4 w-4 text-muted-foreground" />;
  }
};

const getRoleLabel = (role: MemberRole) => {
  switch (role) {
    case 'owner':
      return 'Owner';
    case 'admin':
      return 'Admin';
    default:
      return 'Member';
  }
};

export default function TeamPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInviting, setIsInviting] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'member'>('member');
  const [editingMember, setEditingMember] = useState<string | null>(null);
  const [isEditingOrg, setIsEditingOrg] = useState(false);
  const [orgName, setOrgName] = useState('');
  const [orgDescription, setOrgDescription] = useState('');

  // Check auth
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  // Load organization and members
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const currentOrgId = organizationsApi.getCurrentId();
      if (currentOrgId) {
        const [org, membersList] = await Promise.all([
          organizationsApi.get(currentOrgId),
          organizationsApi.listMembers(currentOrgId),
        ]);
        setOrganization(org);
        setMembers(membersList);
        setOrgName(org.name);
        setOrgDescription(org.description || '');
      } else {
        // Try to get first organization
        const orgs = await organizationsApi.list();
        if (orgs.length > 0) {
          organizationsApi.switchTo(orgs[0].id);
          const membersList = await organizationsApi.listMembers(orgs[0].id);
          setOrganization(orgs[0]);
          setMembers(membersList);
          setOrgName(orgs[0].name);
          setOrgDescription(orgs[0].description || '');
        }
      }
    } catch (error) {
      console.error('Failed to load team data:', error);
      toast.error('Failed to load team data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated, loadData]);

  // Handle invite
  const handleInvite = async () => {
    if (!organization || !inviteEmail.trim()) return;

    setIsInviting(true);
    try {
      await organizationsApi.inviteMember(organization.id, inviteEmail, inviteRole);
      toast.success(`Invitation sent to ${inviteEmail}`);
      setShowInviteModal(false);
      setInviteEmail('');
      setInviteRole('member');
      loadData();
    } catch (error) {
      console.error('Failed to invite member:', error);
      toast.error('Failed to send invitation');
    } finally {
      setIsInviting(false);
    }
  };

  // Handle role change
  const handleRoleChange = async (memberId: string, userId: string, newRole: 'admin' | 'member') => {
    if (!organization) return;

    try {
      await organizationsApi.updateMemberRole(organization.id, userId, newRole);
      toast.success('Role updated successfully');
      setEditingMember(null);
      loadData();
    } catch (error) {
      console.error('Failed to update role:', error);
      toast.error('Failed to update role');
    }
  };

  // Handle remove member
  const handleRemoveMember = async (userId: string, memberName: string) => {
    if (!organization) return;
    if (!confirm(`Are you sure you want to remove ${memberName} from the team?`)) return;

    try {
      await organizationsApi.removeMember(organization.id, userId);
      toast.success('Member removed');
      loadData();
    } catch (error) {
      console.error('Failed to remove member:', error);
      toast.error('Failed to remove member');
    }
  };

  // Handle org update
  const handleUpdateOrg = async () => {
    if (!organization) return;

    try {
      await organizationsApi.update(organization.id, {
        name: orgName,
        description: orgDescription,
      });
      toast.success('Organization updated');
      setIsEditingOrg(false);
      loadData();
    } catch (error) {
      console.error('Failed to update organization:', error);
      toast.error('Failed to update organization');
    }
  };

  // Copy invite link
  const copyInviteLink = () => {
    if (!organization) return;
    const link = `${window.location.origin}/join/${organization.slug}`;
    navigator.clipboard.writeText(link);
    toast.success('Invite link copied to clipboard');
  };

  if (!isAuthenticated) return null;

  const currentUserMember = members.find((m) => m.user_id === user?.id);
  const isOwnerOrAdmin = currentUserMember?.role === 'owner' || currentUserMember?.role === 'admin';

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Users className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Team</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadData}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Link href="/chat">
              <Button variant="ghost" size="sm">
                Go to Chat
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !organization ? (
          <div className="text-center py-12">
            <Building2 className="mx-auto h-12 w-12 text-muted-foreground" />
            <h2 className="mt-4 text-lg font-medium">No Organization</h2>
            <p className="mt-2 text-muted-foreground">
              Create or join an organization to manage your team
            </p>
            <Button className="mt-4" onClick={() => router.push('/onboarding')}>
              Get Started
            </Button>
          </div>
        ) : (
          <div className="grid gap-8 lg:grid-cols-3">
            {/* Organization Info */}
            <div className="lg:col-span-1">
              <div className="rounded-lg border bg-card p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Organization</h2>
                  {isOwnerOrAdmin && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsEditingOrg(!isEditingOrg)}
                    >
                      <Settings className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                {isEditingOrg ? (
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Name</label>
                      <Input
                        value={orgName}
                        onChange={(e) => setOrgName(e.target.value)}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium">Description</label>
                      <Input
                        value={orgDescription}
                        onChange={(e) => setOrgDescription(e.target.value)}
                        className="mt-1"
                        placeholder="Optional description"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleUpdateOrg}>
                        Save
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setIsEditingOrg(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Building2 className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-medium">{organization.name}</h3>
                        <p className="text-sm text-muted-foreground">
                          {organization.slug}
                        </p>
                      </div>
                    </div>

                    {organization.description && (
                      <p className="text-sm text-muted-foreground mb-4">
                        {organization.description}
                      </p>
                    )}

                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Plan</span>
                        <span className="font-medium capitalize">{organization.tier}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Members</span>
                        <span className="font-medium">
                          {members.length} / {organization.max_members}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Projects</span>
                        <span className="font-medium">
                          - / {organization.max_projects}
                        </span>
                      </div>
                    </div>

                    <hr className="my-4" />

                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={copyInviteLink}
                    >
                      <Copy className="mr-2 h-4 w-4" />
                      Copy Invite Link
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* Team Members */}
            <div className="lg:col-span-2">
              <div className="rounded-lg border bg-card">
                <div className="flex items-center justify-between p-4 border-b">
                  <h2 className="text-lg font-semibold">
                    Team Members ({members.length})
                  </h2>
                  {isOwnerOrAdmin && (
                    <Button size="sm" onClick={() => setShowInviteModal(true)}>
                      <UserPlus className="mr-2 h-4 w-4" />
                      Invite
                    </Button>
                  )}
                </div>

                <div className="divide-y">
                  {members.map((member) => (
                    <div
                      key={member.id}
                      className="flex items-center justify-between p-4 hover:bg-muted/50"
                    >
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium text-primary">
                          {member.user?.full_name?.charAt(0) ||
                            member.user?.email?.charAt(0) ||
                            'U'}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">
                              {member.user?.full_name || member.user?.email || 'Unknown'}
                            </span>
                            {member.user_id === user?.id && (
                              <span className="text-xs text-muted-foreground">(You)</span>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {member.user?.email}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {editingMember === member.id ? (
                          <div className="flex items-center gap-2">
                            <select
                              className="text-sm border rounded px-2 py-1"
                              defaultValue={member.role}
                              onChange={(e) =>
                                handleRoleChange(
                                  member.id,
                                  member.user_id,
                                  e.target.value as 'admin' | 'member'
                                )
                              }
                            >
                              <option value="admin">Admin</option>
                              <option value="member">Member</option>
                            </select>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setEditingMember(null)}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ) : (
                          <>
                            <div className="flex items-center gap-1.5">
                              {getRoleIcon(member.role as MemberRole)}
                              <span className="text-sm">
                                {getRoleLabel(member.role as MemberRole)}
                              </span>
                            </div>

                            {isOwnerOrAdmin &&
                              member.role !== 'owner' &&
                              member.user_id !== user?.id && (
                                <div className="flex items-center gap-1">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => setEditingMember(member.id)}
                                  >
                                    <Settings className="h-4 w-4" />
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="text-destructive hover:text-destructive"
                                    onClick={() =>
                                      handleRemoveMember(
                                        member.user_id,
                                        member.user?.full_name || member.user?.email || 'this member'
                                      )
                                    }
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </div>
                              )}
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Invite Modal */}
      {showInviteModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onKeyDown={(e) => { if (e.key === 'Escape') setShowInviteModal(false); }}
        >
          <div className="bg-background rounded-lg border shadow-lg w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Invite Team Member</h2>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowInviteModal(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Email Address</label>
                <Input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="mt-1"
                />
              </div>

              <div>
                <label className="text-sm font-medium">Role</label>
                <div className="flex gap-2 mt-1">
                  <button
                    className={cn(
                      'flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
                      inviteRole === 'member'
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'hover:bg-muted'
                    )}
                    onClick={() => setInviteRole('member')}
                  >
                    <User className="h-4 w-4" />
                    Member
                  </button>
                  <button
                    className={cn(
                      'flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors',
                      inviteRole === 'admin'
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'hover:bg-muted'
                    )}
                    onClick={() => setInviteRole('admin')}
                  >
                    <Shield className="h-4 w-4" />
                    Admin
                  </button>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  {inviteRole === 'admin'
                    ? 'Admins can invite members and manage team settings'
                    : 'Members can access all features but cannot manage the team'}
                </p>
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  className="flex-1"
                  onClick={handleInvite}
                  disabled={isInviting || !inviteEmail.trim()}
                >
                  {isInviting ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Mail className="mr-2 h-4 w-4" />
                  )}
                  Send Invitation
                </Button>
                <Button variant="outline" onClick={() => setShowInviteModal(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <FloatingAssistant context="team" />
    </div>
  );
}
