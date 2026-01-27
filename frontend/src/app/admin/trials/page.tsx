'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Clock,
  Users,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  ChevronDown,
  MoreHorizontal,
  Calendar,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
  trialsApi,
  type TrialStatistics,
  type OrganizationTrial,
} from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'All Trials' },
  { value: 'active', label: 'Active' },
  { value: 'expired', label: 'Expired' },
  { value: 'converted', label: 'Converted' },
];

function StatCard({
  title,
  value,
  icon: Icon,
  description,
  variant = 'default',
}: {
  title: string;
  value: string | number;
  icon: typeof Clock;
  description?: string;
  variant?: 'default' | 'warning' | 'success' | 'danger';
}) {
  const variantStyles = {
    default: 'bg-primary/10 text-primary',
    warning: 'bg-amber-500/10 text-amber-500',
    success: 'bg-green-500/10 text-green-500',
    danger: 'bg-red-500/10 text-red-500',
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className={cn('rounded-lg p-2', variantStyles[variant])}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'active':
      return (
        <Badge variant="default" className="bg-green-500">
          <Clock className="mr-1 h-3 w-3" />
          Active
        </Badge>
      );
    case 'expired':
      return (
        <Badge variant="secondary" className="bg-red-500/10 text-red-500">
          <XCircle className="mr-1 h-3 w-3" />
          Expired
        </Badge>
      );
    case 'converted':
      return (
        <Badge variant="secondary" className="bg-blue-500/10 text-blue-500">
          <CheckCircle className="mr-1 h-3 w-3" />
          Converted
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export default function AdminTrialsPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [statistics, setStatistics] = useState<TrialStatistics | null>(null);
  const [trials, setTrials] = useState<OrganizationTrial[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Extend dialog state
  const [extendDialogOpen, setExtendDialogOpen] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<OrganizationTrial | null>(
    null
  );
  const [extendDays, setExtendDays] = useState('7');
  const [extendReason, setExtendReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check if user is admin
  useEffect(() => {
    if (user && user.role !== 'org_admin' && user.role !== 'staff_admin') {
      router.push('/');
    }
  }, [user, router]);

  // Fetch data
  useEffect(() => {
    async function fetchData() {
      setIsLoading(true);
      try {
        const [stats, trialsList] = await Promise.all([
          trialsApi.getStatistics(),
          trialsApi.listAll(statusFilter || undefined),
        ]);
        setStatistics(stats);
        setTrials(trialsList);
      } catch (error) {
        console.error('Failed to fetch trial data:', error);
        toast.error('Failed to load trial data');
      } finally {
        setIsLoading(false);
      }
    }

    if (user?.role === 'org_admin' || user?.role === 'staff_admin') {
      fetchData();
    }
  }, [user, statusFilter]);

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const [stats, trialsList] = await Promise.all([
        trialsApi.getStatistics(),
        trialsApi.listAll(statusFilter || undefined),
      ]);
      setStatistics(stats);
      setTrials(trialsList);
      toast.success('Data refreshed');
    } catch (error) {
      toast.error('Failed to refresh data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExtendTrial = async () => {
    if (!selectedOrg || !extendDays || !extendReason) {
      toast.error('Please fill in all fields');
      return;
    }

    setIsSubmitting(true);
    try {
      await trialsApi.extend(selectedOrg.id, parseInt(extendDays), extendReason);
      toast.success(`Trial extended by ${extendDays} days`);
      setExtendDialogOpen(false);
      setSelectedOrg(null);
      setExtendDays('7');
      setExtendReason('');
      handleRefresh();
    } catch (error) {
      toast.error('Failed to extend trial');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExpireTrial = async (org: OrganizationTrial) => {
    if (
      !confirm(
        `Are you sure you want to expire the trial for "${org.name}"? This will downgrade them to the free tier.`
      )
    ) {
      return;
    }

    try {
      await trialsApi.expire(org.id);
      toast.success('Trial expired successfully');
      handleRefresh();
    } catch (error) {
      toast.error('Failed to expire trial');
    }
  };

  // Filter trials by search query
  const filteredTrials = trials.filter(
    (trial) =>
      trial.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      trial.slug.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (user?.role !== 'org_admin' && user?.role !== 'staff_admin') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p>Access denied. Admin privileges required.</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Trials Dashboard
          </h1>
          <p className="text-muted-foreground">
            Manage and monitor organization trials
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={isLoading}>
          <RefreshCw
            className={cn('mr-2 h-4 w-4', isLoading && 'animate-spin')}
          />
          Refresh
        </Button>
      </div>

      {/* Statistics Cards */}
      {statistics && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Active Trials"
            value={statistics.active}
            icon={Clock}
            description="Currently in trial period"
          />
          <StatCard
            title="Expiring Soon"
            value={statistics.expiring_soon}
            icon={AlertTriangle}
            description="Expiring in next 3 days"
            variant="warning"
          />
          <StatCard
            title="Converted"
            value={statistics.converted}
            icon={CheckCircle}
            description="Converted to paid"
            variant="success"
          />
          <StatCard
            title="Conversion Rate"
            value={`${statistics.conversion_rate}%`}
            icon={TrendingUp}
            description="Of completed trials"
          />
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>All Trials</CardTitle>
          <CardDescription>
            {filteredTrials.length} trial{filteredTrials.length !== 1 ? 's' : ''}{' '}
            found
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex items-center gap-4">
            <Input
              placeholder="Search by name or slug..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="max-w-sm"
            />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline">
                  {STATUS_FILTER_OPTIONS.find((o) => o.value === statusFilter)
                    ?.label || 'Filter'}
                  <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {STATUS_FILTER_OPTIONS.map((option) => (
                  <DropdownMenuItem
                    key={option.value}
                    onClick={() => setStatusFilter(option.value)}
                  >
                    {option.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Trials Table */}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Organization</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Days Left</TableHead>
                  <TableHead>Members</TableHead>
                  <TableHead>Projects</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTrials.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className="text-center text-muted-foreground"
                    >
                      No trials found
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTrials.map((trial) => (
                    <TableRow key={trial.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{trial.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {trial.slug}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>{getStatusBadge(trial.trial_status)}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{trial.tier}</Badge>
                      </TableCell>
                      <TableCell>
                        {trial.trial_status === 'active' ? (
                          <span
                            className={cn(
                              'font-medium',
                              trial.trial_days_remaining <= 3 &&
                                'text-amber-500'
                            )}
                          >
                            {trial.trial_days_remaining} days
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Users className="h-3 w-3 text-muted-foreground" />
                          {trial.current_member_count}
                        </div>
                      </TableCell>
                      <TableCell>{trial.current_project_count}</TableCell>
                      <TableCell>
                        {trial.trial_started_at ? (
                          <span className="text-sm text-muted-foreground">
                            {new Date(
                              trial.trial_started_at
                            ).toLocaleDateString()}
                          </span>
                        ) : (
                          '-'
                        )}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            {trial.trial_status === 'active' && (
                              <>
                                <DropdownMenuItem
                                  onClick={() => {
                                    setSelectedOrg(trial);
                                    setExtendDialogOpen(true);
                                  }}
                                >
                                  <Calendar className="mr-2 h-4 w-4" />
                                  Extend Trial
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  className="text-red-500"
                                  onClick={() => handleExpireTrial(trial)}
                                >
                                  <XCircle className="mr-2 h-4 w-4" />
                                  Expire Trial
                                </DropdownMenuItem>
                              </>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Extend Trial Dialog */}
      <Dialog open={extendDialogOpen} onOpenChange={setExtendDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Extend Trial</DialogTitle>
            <DialogDescription>
              Extend the trial period for {selectedOrg?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Extension Days</label>
              <Input
                type="number"
                min="1"
                max="90"
                value={extendDays}
                onChange={(e) => setExtendDays(e.target.value)}
                placeholder="7"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Reason</label>
              <Input
                value={extendReason}
                onChange={(e) => setExtendReason(e.target.value)}
                placeholder="Customer requested more time to evaluate"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setExtendDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleExtendTrial} disabled={isSubmitting}>
              {isSubmitting ? 'Extending...' : 'Extend Trial'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
