'use client';

import { useState, useEffect } from 'react';
import {
  Settings,
  Save,
  Loader2,
  Globe,
  Shield,
  Bell,
  Database,
} from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface SystemSettings {
  siteName: string;
  maxUsersPerOrg: number;
  defaultTrialDays: number;
  maintenanceMode: boolean;
  allowSignups: boolean;
  requireEmailVerification: boolean;
}

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<SystemSettings>({
    siteName: 'GoSumo',
    maxUsersPerOrg: 50,
    defaultTrialDays: 14,
    maintenanceMode: false,
    allowSignups: true,
    requireEmailVerification: true,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/admin/settings');
      setSettings(response.data);
    } catch {
      toast.error('Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.put('/admin/settings', settings);
      toast.success('Settings saved');
    } catch {
      toast.error('Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const sections = [
    {
      title: 'General',
      icon: Globe,
      fields: [
        {
          label: 'Site Name',
          type: 'text' as const,
          value: settings.siteName,
          onChange: (v: string) => setSettings((s) => ({ ...s, siteName: v })),
        },
        {
          label: 'Max Users per Organization',
          type: 'number' as const,
          value: settings.maxUsersPerOrg,
          onChange: (v: string) =>
            setSettings((s) => ({ ...s, maxUsersPerOrg: parseInt(v) || 0 })),
        },
        {
          label: 'Default Trial Duration (days)',
          type: 'number' as const,
          value: settings.defaultTrialDays,
          onChange: (v: string) =>
            setSettings((s) => ({ ...s, defaultTrialDays: parseInt(v) || 0 })),
        },
      ],
    },
    {
      title: 'Security',
      icon: Shield,
      toggles: [
        {
          label: 'Allow New Signups',
          description: 'Allow new users to register accounts',
          checked: settings.allowSignups,
          onChange: (v: boolean) =>
            setSettings((s) => ({ ...s, allowSignups: v })),
        },
        {
          label: 'Require Email Verification',
          description: 'Users must verify email before accessing the platform',
          checked: settings.requireEmailVerification,
          onChange: (v: boolean) =>
            setSettings((s) => ({ ...s, requireEmailVerification: v })),
        },
      ],
    },
    {
      title: 'Maintenance',
      icon: Database,
      toggles: [
        {
          label: 'Maintenance Mode',
          description: 'Show maintenance page to all non-admin users',
          checked: settings.maintenanceMode,
          onChange: (v: boolean) =>
            setSettings((s) => ({ ...s, maintenanceMode: v })),
        },
      ],
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">System Settings</h1>
          <p className="text-muted-foreground mt-1">
            Configure platform-wide settings
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Save Changes
        </button>
      </div>

      <div className="space-y-8">
        {sections.map((section) => (
          <div key={section.title} className="rounded-xl border bg-card">
            <div className="flex items-center gap-3 p-6 border-b">
              <section.icon className="h-5 w-5 text-muted-foreground" />
              <h2 className="text-lg font-semibold">{section.title}</h2>
            </div>
            <div className="p-6 space-y-6">
              {section.fields?.map((field) => (
                <div key={field.label}>
                  <label className="block text-sm font-medium mb-2">
                    {field.label}
                  </label>
                  <input
                    type={field.type}
                    value={field.value}
                    onChange={(e) => field.onChange(e.target.value)}
                    className="w-full max-w-md rounded-lg border bg-background px-3 py-2 text-sm"
                  />
                </div>
              ))}
              {section.toggles?.map((toggle) => (
                <div
                  key={toggle.label}
                  className="flex items-center justify-between"
                >
                  <div>
                    <p className="font-medium">{toggle.label}</p>
                    <p className="text-sm text-muted-foreground">
                      {toggle.description}
                    </p>
                  </div>
                  <button
                    onClick={() => toggle.onChange(!toggle.checked)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      toggle.checked ? 'bg-primary' : 'bg-muted'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        toggle.checked ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
