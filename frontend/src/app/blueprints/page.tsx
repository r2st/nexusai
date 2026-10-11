'use client';

import { useEffect, useState } from 'react';
import {
  Plus,
  Play,
  Pause,
  Trash2,
  Edit,
  RefreshCw,
  Loader2,
  Calendar,
  Settings,
  CheckCircle,
  XCircle,
  Clock,
  Database,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';

interface Blueprint {
  id: string;
  name: string;
  description: string | null;
  mode: string;
  status: string;
  cron_config: string | null;
  created_at: string;
  updated_at: string;
  connections: Array<{
    plugin: string;
    connection_id: number;
    scopes: string[];
  }>;
}

export default function BlueprintsPage() {
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedBlueprint, setSelectedBlueprint] = useState<Blueprint | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    project_id: '',
    cron_config: '0 0 * * *', // Daily at midnight
    connections: [] as Array<{ plugin: string; connection_id: number; scopes: string[] }>,
  });

  useEffect(() => {
    loadBlueprints();
  }, []);

  const loadBlueprints = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/v1/blueprints', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setBlueprints(data);
      }
    } catch (error) {
      console.error('Failed to load blueprints:', error);
      toast.error('Failed to load blueprints');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      const response = await fetch('/api/v1/blueprints', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          name: formData.name,
          description: formData.description || null,
          project_id: formData.project_id,
          mode: 'NORMAL',
          cron_config: formData.cron_config,
          connections: formData.connections,
        }),
      });

      if (response.ok) {
        const newBlueprint = await response.json();
        setBlueprints((prev) => [newBlueprint, ...prev]);
        setShowCreateModal(false);
        resetForm();
      } else {
        const error = await response.json();
        toast.error(`Failed to create blueprint: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to create blueprint:', error);
      toast.error('Failed to create blueprint');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (blueprintId: string) => {
    if (!confirm('Are you sure you want to delete this blueprint?')) return;

    try {
      const response = await fetch(`/api/v1/blueprints/${blueprintId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        setBlueprints((prev) => prev.filter((b) => b.id !== blueprintId));
      } else {
        toast.error('Failed to delete blueprint');
      }
    } catch {
      toast.error('Failed to delete blueprint');
    }
  };

  const handleTrigger = async (blueprintId: string) => {
    try {
      const response = await fetch(`/api/v1/blueprints/${blueprintId}/trigger`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        toast.success('Blueprint triggered successfully');
        loadBlueprints();
      } else {
        toast.error('Failed to trigger blueprint');
      }
    } catch {
      toast.error('Failed to trigger blueprint');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      project_id: '',
      cron_config: '0 0 * * *',
      connections: [],
    });
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }> = {
      ACTIVE: { variant: 'default', label: 'Active' },
      INACTIVE: { variant: 'secondary', label: 'Inactive' },
      ERROR: { variant: 'destructive', label: 'Error' },
      RUNNING: { variant: 'default', label: 'Running' },
    };

    const config = statusMap[status] || { variant: 'outline' as const, label: status };
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Blueprints</h1>
          <p className="text-muted-foreground mt-2">
            Configure data collection schedules and transformations
          </p>
        </div>
        <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Blueprint
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create Blueprint</DialogTitle>
              <DialogDescription>
                Define a data collection blueprint with connections, scope, and schedule
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="My Blueprint"
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Blueprint description"
                  rows={3}
                />
              </div>
              <div>
                <Label htmlFor="project_id">Project ID</Label>
                <Input
                  id="project_id"
                  value={formData.project_id}
                  onChange={(e) => setFormData({ ...formData, project_id: e.target.value })}
                  placeholder="project-uuid"
                />
              </div>
              <div>
                <Label htmlFor="cron_config">Schedule (Cron)</Label>
                <Input
                  id="cron_config"
                  value={formData.cron_config}
                  onChange={(e) => setFormData({ ...formData, cron_config: e.target.value })}
                  placeholder="0 0 * * *"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Example: 0 0 * * * (daily at midnight)
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowCreateModal(false);
                    resetForm();
                  }}
                >
                  Cancel
                </Button>
                <Button onClick={handleCreate} disabled={isCreating || !formData.name}>
                  {isCreating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Create'
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {blueprints.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No blueprints</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create your first blueprint to start collecting data
            </p>
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Blueprint
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {blueprints.map((blueprint) => (
            <Card key={blueprint.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{blueprint.name}</CardTitle>
                    <CardDescription className="mt-1">
                      {blueprint.description || 'No description'}
                    </CardDescription>
                  </div>
                  {getStatusBadge(blueprint.status)}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>
                      {blueprint.cron_config || 'Manual'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Database className="h-4 w-4" />
                    <span>
                      {blueprint.connections.length} connection(s)
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    <span>
                      Created {new Date(blueprint.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleTrigger(blueprint.id)}
                    className="flex-1"
                  >
                    <Play className="mr-2 h-4 w-4" />
                    Trigger
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDelete(blueprint.id)}
                    aria-label="Delete blueprint"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
