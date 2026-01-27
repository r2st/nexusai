"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Download,
  Trash2,
  Shield,
  Eye,
  EyeOff,
  FileText,
  Clock,
  CheckCircle,
  AlertTriangle,
  Info,
  Lock,
  Globe,
  Database,
  UserX,
  Settings,
  History,
  Bell,
  Mail,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

// Types
interface ConsentItem {
  id: string;
  name: string;
  description: string;
  required: boolean;
  enabled: boolean;
  category: "essential" | "functional" | "analytics" | "marketing";
  lastUpdated: string;
}

interface DataCategory {
  id: string;
  name: string;
  description: string;
  dataTypes: string[];
  retentionPeriod: string;
  purpose: string;
  canDelete: boolean;
  canExport: boolean;
}

interface DataRequest {
  id: string;
  type: "export" | "deletion" | "access" | "rectification";
  status: "pending" | "processing" | "completed" | "rejected";
  createdAt: string;
  completedAt?: string;
  downloadUrl?: string;
}

interface AccessLog {
  id: string;
  action: string;
  resource: string;
  timestamp: string;
  ipAddress: string;
  userAgent: string;
}

// Mock data
const CONSENT_ITEMS: ConsentItem[] = [
  {
    id: "essential",
    name: "Essential Cookies",
    description: "Required for the platform to function properly",
    required: true,
    enabled: true,
    category: "essential",
    lastUpdated: "2026-01-01",
  },
  {
    id: "analytics",
    name: "Analytics & Performance",
    description: "Help us understand how you use the platform to improve it",
    required: false,
    enabled: true,
    category: "analytics",
    lastUpdated: "2026-01-15",
  },
  {
    id: "ai_training",
    name: "AI Model Improvement",
    description: "Allow anonymized data to improve AI models",
    required: false,
    enabled: false,
    category: "functional",
    lastUpdated: "2026-01-10",
  },
  {
    id: "marketing",
    name: "Marketing Communications",
    description: "Receive product updates and promotional content",
    required: false,
    enabled: false,
    category: "marketing",
    lastUpdated: "2026-01-05",
  },
  {
    id: "third_party",
    name: "Third-Party Integrations",
    description: "Share data with connected services (GitHub, Jira, etc.)",
    required: false,
    enabled: true,
    category: "functional",
    lastUpdated: "2026-01-12",
  },
];

const DATA_CATEGORIES: DataCategory[] = [
  {
    id: "profile",
    name: "Profile Information",
    description: "Your account details and preferences",
    dataTypes: ["Name", "Email", "Avatar", "Preferences"],
    retentionPeriod: "Until account deletion",
    purpose: "Account management and personalization",
    canDelete: true,
    canExport: true,
  },
  {
    id: "activity",
    name: "Activity Data",
    description: "Your interactions with the platform",
    dataTypes: ["Chat history", "Searches", "Code analysis requests"],
    retentionPeriod: "90 days",
    purpose: "Service improvement and personalization",
    canDelete: true,
    canExport: true,
  },
  {
    id: "analytics",
    name: "Usage Analytics",
    description: "Anonymized usage statistics",
    dataTypes: ["Page views", "Feature usage", "Performance metrics"],
    retentionPeriod: "1 year",
    purpose: "Product improvement",
    canDelete: false,
    canExport: true,
  },
  {
    id: "integrations",
    name: "Integration Data",
    description: "Data from connected services",
    dataTypes: ["Repository metadata", "PR information", "Ticket data"],
    retentionPeriod: "Until disconnected + 30 days",
    purpose: "Providing AI-powered insights",
    canDelete: true,
    canExport: true,
  },
  {
    id: "billing",
    name: "Billing Information",
    description: "Payment and subscription data",
    dataTypes: ["Payment method (last 4 digits)", "Invoices", "Subscription"],
    retentionPeriod: "7 years (legal requirement)",
    purpose: "Billing and compliance",
    canDelete: false,
    canExport: true,
  },
];

const DATA_REQUESTS: DataRequest[] = [
  {
    id: "req-1",
    type: "export",
    status: "completed",
    createdAt: "2026-01-15T10:30:00Z",
    completedAt: "2026-01-15T10:35:00Z",
    downloadUrl: "/downloads/export-123.zip",
  },
  {
    id: "req-2",
    type: "deletion",
    status: "pending",
    createdAt: "2026-01-19T14:00:00Z",
  },
];

const ACCESS_LOGS: AccessLog[] = [
  {
    id: "log-1",
    action: "Login",
    resource: "Account",
    timestamp: "2026-01-19T16:30:00Z",
    ipAddress: "192.168.1.***",
    userAgent: "Chrome 120 / macOS",
  },
  {
    id: "log-2",
    action: "View",
    resource: "Code Analysis Report",
    timestamp: "2026-01-19T16:25:00Z",
    ipAddress: "192.168.1.***",
    userAgent: "Chrome 120 / macOS",
  },
  {
    id: "log-3",
    action: "Export",
    resource: "Personal Data",
    timestamp: "2026-01-15T10:30:00Z",
    ipAddress: "192.168.1.***",
    userAgent: "Chrome 120 / macOS",
  },
  {
    id: "log-4",
    action: "Update",
    resource: "Consent Preferences",
    timestamp: "2026-01-10T09:15:00Z",
    ipAddress: "192.168.1.***",
    userAgent: "Firefox 121 / Windows",
  },
];

// Consent Manager Component
function ConsentManager({
  consents,
  onUpdate,
}: {
  consents: ConsentItem[];
  onUpdate: (id: string, enabled: boolean) => void;
}) {
  const categories = {
    essential: { label: "Essential", icon: Lock },
    functional: { label: "Functional", icon: Settings },
    analytics: { label: "Analytics", icon: Eye },
    marketing: { label: "Marketing", icon: Mail },
  };

  return (
    <div className="space-y-6">
      {Object.entries(categories).map(([category, config]) => {
        const Icon = config.icon;
        const items = consents.filter((c) => c.category === category);
        if (items.length === 0) return null;

        return (
          <div key={category}>
            <div className="flex items-center gap-2 mb-3">
              <Icon className="h-4 w-4 text-muted-foreground" />
              <h4 className="font-medium">{config.label}</h4>
            </div>
            <div className="space-y-3">
              {items.map((consent) => (
                <div
                  key={consent.id}
                  className="flex items-start justify-between p-4 border rounded-lg"
                >
                  <div className="flex-1 pr-4">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{consent.name}</p>
                      {consent.required && (
                        <Badge variant="secondary" className="text-xs">
                          Required
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {consent.description}
                    </p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Last updated: {new Date(consent.lastUpdated).toLocaleDateString()}
                    </p>
                  </div>
                  <Switch
                    checked={consent.enabled}
                    disabled={consent.required}
                    onCheckedChange={(checked) => onUpdate(consent.id, checked)}
                  />
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Data Inventory Component
function DataInventory({ categories }: { categories: DataCategory[] }) {
  return (
    <div className="space-y-4">
      {categories.map((category) => (
        <Card key={category.id}>
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-base">{category.name}</CardTitle>
                <CardDescription>{category.description}</CardDescription>
              </div>
              <div className="flex gap-2">
                {category.canExport && (
                  <Badge variant="outline" className="text-xs">
                    <Download className="h-3 w-3 mr-1" />
                    Exportable
                  </Badge>
                )}
                {category.canDelete && (
                  <Badge variant="outline" className="text-xs">
                    <Trash2 className="h-3 w-3 mr-1" />
                    Deletable
                  </Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground mb-1">Data Types</p>
                <div className="flex flex-wrap gap-1">
                  {category.dataTypes.map((type) => (
                    <Badge key={type} variant="secondary" className="text-xs">
                      {type}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-muted-foreground mb-1">Retention Period</p>
                <p>{category.retentionPeriod}</p>
              </div>
              <div className="col-span-2">
                <p className="text-muted-foreground mb-1">Purpose</p>
                <p>{category.purpose}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// Data Request Component
function DataRequestSection({
  requests,
  onNewRequest,
}: {
  requests: DataRequest[];
  onNewRequest: (type: DataRequest["type"], reason?: string) => void;
}) {
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteReason, setDeleteReason] = useState("");
  const [exportFormat, setExportFormat] = useState("json");

  const handleExport = () => {
    onNewRequest("export");
    setShowExportDialog(false);
    toast.success("Export request submitted. You'll be notified when ready.");
  };

  const handleDelete = () => {
    onNewRequest("deletion", deleteReason);
    setShowDeleteDialog(false);
    setDeleteReason("");
    toast.success("Deletion request submitted. This may take up to 30 days.");
  };

  return (
    <div className="space-y-6">
      {/* Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Download className="h-4 w-4" />
              Export Your Data
            </CardTitle>
            <CardDescription>
              Download a copy of all your personal data
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Dialog open={showExportDialog} onOpenChange={setShowExportDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" className="w-full">
                  Request Export
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Export Your Data</DialogTitle>
                  <DialogDescription>
                    We'll prepare a download of all your personal data. This
                    usually takes a few minutes.
                  </DialogDescription>
                </DialogHeader>
                <div className="py-4">
                  <Label>Export Format</Label>
                  <Select value={exportFormat} onValueChange={setExportFormat}>
                    <SelectTrigger className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="json">JSON (machine-readable)</SelectItem>
                      <SelectItem value="csv">CSV (spreadsheet)</SelectItem>
                      <SelectItem value="pdf">PDF (human-readable)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground mt-2">
                    The export will include: profile data, activity history,
                    consent records, and integration data.
                  </p>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowExportDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleExport}>
                    <Download className="h-4 w-4 mr-2" />
                    Start Export
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </CardFooter>
        </Card>

        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2 text-destructive">
              <Trash2 className="h-4 w-4" />
              Delete Your Data
            </CardTitle>
            <CardDescription>
              Request permanent deletion of your account and data
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" className="w-full">
                  Request Deletion
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Your Account?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. Your account and all associated
                    data will be permanently deleted within 30 days.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <div className="py-4">
                  <Label>Reason for leaving (optional)</Label>
                  <Textarea
                    className="mt-2"
                    placeholder="Help us improve by sharing why you're leaving..."
                    value={deleteReason}
                    onChange={(e) => setDeleteReason(e.target.value)}
                  />
                  <div className="mt-4 p-3 bg-destructive/10 rounded-lg">
                    <p className="text-sm font-medium text-destructive flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Warning
                    </p>
                    <ul className="text-sm text-muted-foreground mt-2 space-y-1 ml-6 list-disc">
                      <li>All your data will be permanently erased</li>
                      <li>Active subscriptions will be cancelled</li>
                      <li>Connected integrations will be disconnected</li>
                      <li>This cannot be reversed</li>
                    </ul>
                  </div>
                </div>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleDelete}
                    className="bg-destructive hover:bg-destructive/90"
                  >
                    Yes, Delete My Account
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </CardFooter>
        </Card>
      </div>

      {/* Request History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Request History</CardTitle>
          <CardDescription>Track the status of your data requests</CardDescription>
        </CardHeader>
        <CardContent>
          {requests.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No data requests yet
            </p>
          ) : (
            <div className="space-y-3">
              {requests.map((request) => (
                <div
                  key={request.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {request.type === "export" ? (
                      <Download className="h-4 w-4 text-blue-500" />
                    ) : request.type === "deletion" ? (
                      <Trash2 className="h-4 w-4 text-red-500" />
                    ) : (
                      <Eye className="h-4 w-4 text-gray-500" />
                    )}
                    <div>
                      <p className="font-medium capitalize">
                        {request.type} Request
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(request.createdAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={
                        request.status === "completed"
                          ? "default"
                          : request.status === "processing"
                          ? "secondary"
                          : request.status === "rejected"
                          ? "destructive"
                          : "outline"
                      }
                    >
                      {request.status === "pending" && (
                        <Clock className="h-3 w-3 mr-1" />
                      )}
                      {request.status === "completed" && (
                        <CheckCircle className="h-3 w-3 mr-1" />
                      )}
                      {request.status}
                    </Badge>
                    {request.downloadUrl && (
                      <Button size="sm" variant="outline">
                        <Download className="h-3 w-3 mr-1" />
                        Download
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Access Logs Component
function AccessLogs({ logs }: { logs: AccessLog[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Data Access Log</CardTitle>
            <CardDescription>
              Recent access to your personal data
            </CardDescription>
          </div>
          <Button variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px]">
          <div className="space-y-2">
            {logs.map((log) => (
              <div
                key={log.id}
                className="flex items-start justify-between p-3 border rounded-lg text-sm"
              >
                <div>
                  <p className="font-medium">
                    {log.action}: {log.resource}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1">
                    <span>{new Date(log.timestamp).toLocaleString()}</span>
                    <span>IP: {log.ipAddress}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {log.userAgent}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// Main Privacy Dashboard Component
export function PrivacyDashboard() {
  const [consents, setConsents] = useState(CONSENT_ITEMS);
  const [requests, setRequests] = useState(DATA_REQUESTS);

  const handleConsentUpdate = (id: string, enabled: boolean) => {
    setConsents(
      consents.map((c) => (c.id === id ? { ...c, enabled } : c))
    );
    toast.success("Consent preferences updated");
  };

  const handleNewRequest = (type: DataRequest["type"], reason?: string) => {
    const newRequest: DataRequest = {
      id: `req-${Date.now()}`,
      type,
      status: "pending",
      createdAt: new Date().toISOString(),
    };
    setRequests([newRequest, ...requests]);
  };

  const consentProgress = Math.round(
    (consents.filter((c) => c.enabled).length / consents.length) * 100
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Privacy Center
          </h2>
          <p className="text-muted-foreground mt-1">
            Manage your privacy settings and personal data
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          <Globe className="h-3 w-3 mr-1" />
          GDPR Compliant
        </Badge>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Data Consents</p>
                <p className="text-2xl font-bold">{consentProgress}%</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500 opacity-50" />
            </div>
            <Progress value={consentProgress} className="mt-3" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Data Categories</p>
                <p className="text-2xl font-bold">{DATA_CATEGORIES.length}</p>
              </div>
              <Database className="h-8 w-8 text-blue-500 opacity-50" />
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              {DATA_CATEGORIES.filter((c) => c.canDelete).length} deletable
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pending Requests</p>
                <p className="text-2xl font-bold">
                  {requests.filter((r) => r.status === "pending").length}
                </p>
              </div>
              <Clock className="h-8 w-8 text-orange-500 opacity-50" />
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              {requests.filter((r) => r.status === "completed").length} completed
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="consent">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="consent">
            <Settings className="h-4 w-4 mr-2" />
            Consent
          </TabsTrigger>
          <TabsTrigger value="data">
            <Database className="h-4 w-4 mr-2" />
            Your Data
          </TabsTrigger>
          <TabsTrigger value="requests">
            <FileText className="h-4 w-4 mr-2" />
            Requests
          </TabsTrigger>
          <TabsTrigger value="logs">
            <History className="h-4 w-4 mr-2" />
            Access Log
          </TabsTrigger>
        </TabsList>

        <TabsContent value="consent" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Consent Preferences</CardTitle>
              <CardDescription>
                Control how we use your data. Required consents cannot be disabled.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ConsentManager consents={consents} onUpdate={handleConsentUpdate} />
            </CardContent>
            <CardFooter className="flex justify-between border-t pt-6">
              <p className="text-xs text-muted-foreground">
                Last updated: {new Date().toLocaleDateString()}
              </p>
              <Button>Save Preferences</Button>
            </CardFooter>
          </Card>
        </TabsContent>

        <TabsContent value="data" className="mt-6">
          <DataInventory categories={DATA_CATEGORIES} />
        </TabsContent>

        <TabsContent value="requests" className="mt-6">
          <DataRequestSection requests={requests} onNewRequest={handleNewRequest} />
        </TabsContent>

        <TabsContent value="logs" className="mt-6">
          <AccessLogs logs={ACCESS_LOGS} />
        </TabsContent>
      </Tabs>

      {/* Info Banner */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <Info className="h-5 w-5 text-blue-500 mt-0.5" />
            <div>
              <p className="font-medium">Your Privacy Rights</p>
              <p className="text-sm text-muted-foreground mt-1">
                Under GDPR and similar regulations, you have the right to access,
                rectify, delete, and port your personal data. You can exercise
                these rights at any time using the controls above. For questions,
                contact{" "}
                <a href="mailto:privacy@nexusai.dev" className="text-primary underline">
                  privacy@nexusai.dev
                </a>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default PrivacyDashboard;
