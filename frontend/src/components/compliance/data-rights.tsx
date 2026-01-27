'use client';

import { useState } from 'react';
import {
  Download,
  Trash2,
  Edit,
  Eye,
  Ban,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import {
  useDataSubjectRights,
  useDataExport,
  useDataDeletion,
  DSR_CONFIG,
  getDSRStatusLabel,
  getDSRStatusColor,
  getDaysRemaining,
  isDSROverdue,
  type DSRType,
  type DataSubjectRequest,
} from '@/lib/compliance';

// =============================================================================
// DATA RIGHTS DASHBOARD
// =============================================================================

export function DataRightsDashboard() {
  const {
    requests,
    loading,
    error,
    submitRequest,
    cancelRequest,
    downloadExport,
    refreshRequests,
  } = useDataSubjectRights();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Your Data Rights</h2>
          <p className="text-sm text-muted-foreground">
            Exercise your GDPR data subject rights
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refreshRequests}>
          Refresh
        </Button>
      </div>

      {/* Rights Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <DataRightCard
          icon={<Eye className="h-5 w-5" />}
          title="Access Your Data"
          description="Get a copy of all personal data we hold about you"
          article="Article 15"
          onRequest={() => submitRequest('access')}
        />
        <DataRightCard
          icon={<Download className="h-5 w-5" />}
          title="Export Your Data"
          description="Download your data in a portable format"
          article="Article 20"
          onRequest={() => submitRequest('portability')}
        />
        <DataRightCard
          icon={<Edit className="h-5 w-5" />}
          title="Correct Your Data"
          description="Request corrections to inaccurate data"
          article="Article 16"
          onRequest={() => submitRequest('rectification')}
        />
        <DataRightCard
          icon={<Trash2 className="h-5 w-5" />}
          title="Delete Your Data"
          description="Request deletion of your personal data"
          article="Article 17"
          onRequest={() => submitRequest('erasure')}
          variant="destructive"
        />
        <DataRightCard
          icon={<Ban className="h-5 w-5" />}
          title="Restrict Processing"
          description="Limit how we process your data"
          article="Article 18"
          onRequest={() => submitRequest('restriction')}
        />
        <DataRightCard
          icon={<FileText className="h-5 w-5" />}
          title="Object to Processing"
          description="Object to specific types of data processing"
          article="Article 21"
          onRequest={() => submitRequest('objection')}
        />
      </div>

      {/* Request History */}
      <div className="space-y-4">
        <h3 className="font-semibold">Request History</h3>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-center py-8 text-destructive">{error}</div>
        ) : requests.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No requests submitted yet
          </div>
        ) : (
          <div className="space-y-3">
            {requests.map((request) => (
              <RequestCard
                key={request.id}
                request={request}
                onCancel={() => cancelRequest(request.id)}
                onDownload={() => downloadExport(request.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// DATA RIGHT CARD
// =============================================================================

interface DataRightCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  article: string;
  onRequest: () => void;
  variant?: 'default' | 'destructive';
}

function DataRightCard({
  icon,
  title,
  description,
  article,
  onRequest,
  variant = 'default',
}: DataRightCardProps) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleRequest = async () => {
    setSubmitting(true);
    try {
      await onRequest();
      setOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          className={cn(
            'p-4 rounded-lg border text-left transition-colors hover:bg-muted/50',
            variant === 'destructive' && 'border-destructive/50 hover:border-destructive'
          )}
        >
          <div className={cn(
            'flex items-center gap-2 mb-2',
            variant === 'destructive' ? 'text-destructive' : 'text-primary'
          )}>
            {icon}
            <span className="font-medium">{title}</span>
          </div>
          <p className="text-sm text-muted-foreground">{description}</p>
          <p className="text-xs text-muted-foreground mt-2">{article}</p>
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-muted-foreground">
            This request will be processed within 30 days as required by GDPR.
            You will receive confirmation via email.
          </p>
          {variant === 'destructive' && (
            <div className="mt-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
              <AlertCircle className="h-4 w-4 inline mr-2" />
              Warning: This action may result in permanent deletion of your data.
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            variant={variant === 'destructive' ? 'destructive' : 'default'}
            onClick={handleRequest}
            disabled={submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Submitting...
              </>
            ) : (
              'Submit Request'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// =============================================================================
// REQUEST CARD
// =============================================================================

interface RequestCardProps {
  request: DataSubjectRequest;
  onCancel: () => void;
  onDownload: () => void;
}

function RequestCard({ request, onCancel, onDownload }: RequestCardProps) {
  const config = DSR_CONFIG[request.type];
  const statusColor = getDSRStatusColor(request.status);
  const daysRemaining = getDaysRemaining(request);
  const overdue = isDSROverdue(request);

  const StatusIcon = {
    pending: Clock,
    in_progress: Loader2,
    completed: CheckCircle2,
    rejected: XCircle,
    expired: AlertCircle,
  }[request.status];

  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className={cn(
            'p-2 rounded-lg',
            statusColor === 'green' && 'bg-green-100 text-green-700',
            statusColor === 'yellow' && 'bg-yellow-100 text-yellow-700',
            statusColor === 'blue' && 'bg-blue-100 text-blue-700',
            statusColor === 'red' && 'bg-red-100 text-red-700',
            statusColor === 'gray' && 'bg-gray-100 text-gray-700'
          )}>
            <StatusIcon className={cn(
              'h-4 w-4',
              request.status === 'in_progress' && 'animate-spin'
            )} />
          </div>
          <div>
            <h4 className="font-medium">{config.name}</h4>
            <p className="text-sm text-muted-foreground">
              {getDSRStatusLabel(request.status)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Submitted: {new Date(request.submittedAt).toLocaleDateString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {request.status === 'completed' && request.dataExport && (
            <Button size="sm" variant="outline" onClick={onDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          )}
          {request.status === 'pending' && (
            <Button size="sm" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Progress indicator */}
      {(request.status === 'pending' || request.status === 'in_progress') && (
        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center justify-between text-sm">
            <span className={cn(
              overdue ? 'text-destructive' : 'text-muted-foreground'
            )}>
              {overdue ? 'Overdue' : `${daysRemaining} days remaining`}
            </span>
            <span className="text-muted-foreground">
              Due: {new Date(request.dueDate).toLocaleDateString()}
            </span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                overdue ? 'bg-destructive' : 'bg-primary'
              )}
              style={{
                width: `${Math.min(100, ((30 - daysRemaining) / 30) * 100)}%`,
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// QUICK DATA EXPORT BUTTON
// =============================================================================

export function QuickDataExportButton() {
  const { requestExport, submitting, request, error } = useDataExport();

  if (request) {
    return (
      <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <CheckCircle2 className="h-4 w-4 text-green-500" />
        Export requested
      </div>
    );
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => requestExport('json')}
      disabled={submitting}
    >
      {submitting ? (
        <>
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          Requesting...
        </>
      ) : (
        <>
          <Download className="h-4 w-4 mr-2" />
          Export My Data
        </>
      )}
    </Button>
  );
}

// =============================================================================
// DELETE ACCOUNT DIALOG
// =============================================================================

export function DeleteAccountDialog() {
  const { requestDeletion, submitting, submitted, error } = useDataDeletion();
  const [open, setOpen] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const handleDelete = async () => {
    await requestDeletion(undefined, 'User requested account deletion');
    // Don't close dialog, show confirmation
  };

  if (submitted) {
    return (
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="destructive" size="sm">
            <Trash2 className="h-4 w-4 mr-2" />
            Delete Account
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deletion Request Submitted</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 text-green-700">
              <CheckCircle2 className="h-5 w-5" />
              <p className="text-sm">
                Your account deletion request has been submitted.
                We will process it within 30 days.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive" size="sm">
          <Trash2 className="h-4 w-4 mr-2" />
          Delete Account
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Your Account</DialogTitle>
          <DialogDescription>
            This will permanently delete your account and all associated data.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4 space-y-4">
          <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
            <AlertCircle className="h-4 w-4 inline mr-2" />
            This action cannot be undone. All your data will be permanently deleted.
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium">This includes:</p>
            <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
              <li>Your profile and account information</li>
              <li>All chat conversations and history</li>
              <li>Uploaded documents and files</li>
              <li>API keys and integrations</li>
              <li>Usage analytics and preferences</li>
            </ul>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            <span className="text-sm">
              I understand this action is permanent and cannot be undone
            </span>
          </label>

          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
              {error}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={!confirmed || submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete My Account'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
