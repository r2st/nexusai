/**
 * Settings Page Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock types
interface Profile {
  name: string;
  email: string;
  avatar?: string;
}

interface Settings {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notifications: {
    email: boolean;
    push: boolean;
    desktop: boolean;
  };
}

interface SettingsPageProps {
  profile?: Profile;
  settings?: Settings;
  onUpdateProfile?: (profile: Profile) => Promise<void>;
  onUpdateSettings?: (settings: Settings) => Promise<void>;
  onChangePassword?: (current: string, newPassword: string) => Promise<void>;
  onDeleteAccount?: () => Promise<void>;
  isLoading?: boolean;
}

const defaultProfile: Profile = {
  name: 'John Doe',
  email: 'john@example.com',
};

const defaultSettings: Settings = {
  theme: 'system',
  language: 'en',
  notifications: {
    email: true,
    push: true,
    desktop: true,
  },
};

// Mock SettingsPage component
const SettingsPage = ({
  profile = defaultProfile,
  settings = defaultSettings,
  onUpdateProfile,
  onUpdateSettings,
  onChangePassword,
  onDeleteAccount,
  isLoading = false,
}: SettingsPageProps) => {
  const [activeTab, setActiveTab] = React.useState('profile');
  const [name, setName] = React.useState(profile.name);
  const [currentPassword, setCurrentPassword] = React.useState('');
  const [newPassword, setNewPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      await onUpdateProfile?.({ ...profile, name });
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) return;
    setIsSaving(true);
    try {
      await onChangePassword?.(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } finally {
      setIsSaving(false);
    }
  };

  const handleThemeChange = async (theme: Settings['theme']) => {
    await onUpdateSettings?.({ ...settings, theme });
  };

  if (isLoading) {
    return <div data-testid="loading">Loading settings...</div>;
  }

  return (
    <div data-testid="settings-page" className="settings-page">
      <h1>Settings</h1>

      <nav data-testid="settings-tabs" className="tabs">
        <button
          data-testid="tab-profile"
          className={activeTab === 'profile' ? 'active' : ''}
          onClick={() => setActiveTab('profile')}
        >
          Profile
        </button>
        <button
          data-testid="tab-preferences"
          className={activeTab === 'preferences' ? 'active' : ''}
          onClick={() => setActiveTab('preferences')}
        >
          Preferences
        </button>
        <button
          data-testid="tab-security"
          className={activeTab === 'security' ? 'active' : ''}
          onClick={() => setActiveTab('security')}
        >
          Security
        </button>
        <button
          data-testid="tab-notifications"
          className={activeTab === 'notifications' ? 'active' : ''}
          onClick={() => setActiveTab('notifications')}
        >
          Notifications
        </button>
      </nav>

      {activeTab === 'profile' && (
        <section data-testid="profile-section">
          <h2>Profile</h2>
          <div className="form-group">
            <label htmlFor="name">Name</label>
            <input
              id="name"
              data-testid="name-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              data-testid="email-input"
              type="email"
              value={profile.email}
              disabled
            />
          </div>
          <button data-testid="save-profile" onClick={handleSaveProfile} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Profile'}
          </button>
        </section>
      )}

      {activeTab === 'preferences' && (
        <section data-testid="preferences-section">
          <h2>Preferences</h2>
          <div className="form-group">
            <label>Theme</label>
            <div className="theme-options">
              <label>
                <input
                  type="radio"
                  data-testid="theme-light"
                  name="theme"
                  value="light"
                  checked={settings.theme === 'light'}
                  onChange={() => handleThemeChange('light')}
                />
                Light
              </label>
              <label>
                <input
                  type="radio"
                  data-testid="theme-dark"
                  name="theme"
                  value="dark"
                  checked={settings.theme === 'dark'}
                  onChange={() => handleThemeChange('dark')}
                />
                Dark
              </label>
              <label>
                <input
                  type="radio"
                  data-testid="theme-system"
                  name="theme"
                  value="system"
                  checked={settings.theme === 'system'}
                  onChange={() => handleThemeChange('system')}
                />
                System
              </label>
            </div>
          </div>
        </section>
      )}

      {activeTab === 'security' && (
        <section data-testid="security-section">
          <h2>Security</h2>
          <div className="form-group">
            <label>Change Password</label>
            <input
              data-testid="current-password"
              type="password"
              placeholder="Current password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <input
              data-testid="new-password"
              type="password"
              placeholder="New password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <input
              data-testid="confirm-password"
              type="password"
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            <button
              data-testid="change-password-btn"
              onClick={handleChangePassword}
              disabled={!currentPassword || !newPassword || newPassword !== confirmPassword}
            >
              Change Password
            </button>
          </div>

          <div className="danger-zone">
            <h3>Danger Zone</h3>
            <button
              data-testid="delete-account-btn"
              className="danger"
              onClick={() => setShowDeleteConfirm(true)}
            >
              Delete Account
            </button>
          </div>

          {showDeleteConfirm && (
            <div data-testid="delete-confirm-dialog">
              <p>Are you sure you want to delete your account? This cannot be undone.</p>
              <button data-testid="confirm-delete" onClick={onDeleteAccount}>
                Yes, Delete
              </button>
              <button data-testid="cancel-delete" onClick={() => setShowDeleteConfirm(false)}>
                Cancel
              </button>
            </div>
          )}
        </section>
      )}

      {activeTab === 'notifications' && (
        <section data-testid="notifications-section">
          <h2>Notifications</h2>
          <label>
            <input
              type="checkbox"
              data-testid="notif-email"
              checked={settings.notifications.email}
              onChange={() =>
                onUpdateSettings?.({
                  ...settings,
                  notifications: { ...settings.notifications, email: !settings.notifications.email },
                })
              }
            />
            Email notifications
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="notif-push"
              checked={settings.notifications.push}
              onChange={() =>
                onUpdateSettings?.({
                  ...settings,
                  notifications: { ...settings.notifications, push: !settings.notifications.push },
                })
              }
            />
            Push notifications
          </label>
          <label>
            <input
              type="checkbox"
              data-testid="notif-desktop"
              checked={settings.notifications.desktop}
              onChange={() =>
                onUpdateSettings?.({
                  ...settings,
                  notifications: { ...settings.notifications, desktop: !settings.notifications.desktop },
                })
              }
            />
            Desktop notifications
          </label>
        </section>
      )}
    </div>
  );
};

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders settings page', () => {
    render(<SettingsPage />);
    expect(screen.getByTestId('settings-page')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<SettingsPage isLoading={true} />);
    expect(screen.getByTestId('loading')).toHaveTextContent('Loading settings...');
  });

  it('renders tab navigation', () => {
    render(<SettingsPage />);
    expect(screen.getByTestId('settings-tabs')).toBeInTheDocument();
    expect(screen.getByTestId('tab-profile')).toBeInTheDocument();
    expect(screen.getByTestId('tab-preferences')).toBeInTheDocument();
    expect(screen.getByTestId('tab-security')).toBeInTheDocument();
    expect(screen.getByTestId('tab-notifications')).toBeInTheDocument();
  });

  it('shows profile section by default', () => {
    render(<SettingsPage />);
    expect(screen.getByTestId('profile-section')).toBeInTheDocument();
  });

  it('switches to preferences tab', () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByTestId('tab-preferences'));
    expect(screen.getByTestId('preferences-section')).toBeInTheDocument();
  });

  it('switches to security tab', () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByTestId('tab-security'));
    expect(screen.getByTestId('security-section')).toBeInTheDocument();
  });

  it('switches to notifications tab', () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByTestId('tab-notifications'));
    expect(screen.getByTestId('notifications-section')).toBeInTheDocument();
  });

  describe('Profile Tab', () => {
    it('displays current name', () => {
      render(<SettingsPage profile={defaultProfile} />);
      expect(screen.getByTestId('name-input')).toHaveValue('John Doe');
    });

    it('displays current email (disabled)', () => {
      render(<SettingsPage profile={defaultProfile} />);
      const emailInput = screen.getByTestId('email-input');
      expect(emailInput).toHaveValue('john@example.com');
      expect(emailInput).toBeDisabled();
    });

    it('updates name input', () => {
      render(<SettingsPage />);
      fireEvent.change(screen.getByTestId('name-input'), { target: { value: 'Jane Doe' } });
      expect(screen.getByTestId('name-input')).toHaveValue('Jane Doe');
    });

    it('calls onUpdateProfile when save is clicked', async () => {
      const onUpdateProfile = vi.fn().mockResolvedValue(undefined);
      render(<SettingsPage onUpdateProfile={onUpdateProfile} />);
      
      fireEvent.change(screen.getByTestId('name-input'), { target: { value: 'New Name' } });
      fireEvent.click(screen.getByTestId('save-profile'));

      await waitFor(() => {
        expect(onUpdateProfile).toHaveBeenCalled();
      });
    });
  });

  describe('Preferences Tab', () => {
    it('displays theme options', () => {
      render(<SettingsPage settings={defaultSettings} />);
      fireEvent.click(screen.getByTestId('tab-preferences'));
      
      expect(screen.getByTestId('theme-light')).toBeInTheDocument();
      expect(screen.getByTestId('theme-dark')).toBeInTheDocument();
      expect(screen.getByTestId('theme-system')).toBeInTheDocument();
    });

    it('shows current theme as selected', () => {
      render(<SettingsPage settings={defaultSettings} />);
      fireEvent.click(screen.getByTestId('tab-preferences'));
      
      expect(screen.getByTestId('theme-system')).toBeChecked();
    });

    it('calls onUpdateSettings when theme changes', async () => {
      const onUpdateSettings = vi.fn().mockResolvedValue(undefined);
      render(<SettingsPage settings={defaultSettings} onUpdateSettings={onUpdateSettings} />);
      fireEvent.click(screen.getByTestId('tab-preferences'));
      
      fireEvent.click(screen.getByTestId('theme-dark'));

      await waitFor(() => {
        expect(onUpdateSettings).toHaveBeenCalledWith(expect.objectContaining({ theme: 'dark' }));
      });
    });
  });

  describe('Security Tab', () => {
    it('renders password change form', () => {
      render(<SettingsPage />);
      fireEvent.click(screen.getByTestId('tab-security'));
      
      expect(screen.getByTestId('current-password')).toBeInTheDocument();
      expect(screen.getByTestId('new-password')).toBeInTheDocument();
      expect(screen.getByTestId('confirm-password')).toBeInTheDocument();
    });

    it('disables change password button when passwords do not match', () => {
      render(<SettingsPage />);
      fireEvent.click(screen.getByTestId('tab-security'));
      
      fireEvent.change(screen.getByTestId('current-password'), { target: { value: 'old' } });
      fireEvent.change(screen.getByTestId('new-password'), { target: { value: 'new1' } });
      fireEvent.change(screen.getByTestId('confirm-password'), { target: { value: 'new2' } });

      expect(screen.getByTestId('change-password-btn')).toBeDisabled();
    });

    it('enables change password button when form is valid', () => {
      render(<SettingsPage />);
      fireEvent.click(screen.getByTestId('tab-security'));
      
      fireEvent.change(screen.getByTestId('current-password'), { target: { value: 'old' } });
      fireEvent.change(screen.getByTestId('new-password'), { target: { value: 'new' } });
      fireEvent.change(screen.getByTestId('confirm-password'), { target: { value: 'new' } });

      expect(screen.getByTestId('change-password-btn')).not.toBeDisabled();
    });

    it('shows delete account confirmation', () => {
      render(<SettingsPage />);
      fireEvent.click(screen.getByTestId('tab-security'));
      fireEvent.click(screen.getByTestId('delete-account-btn'));
      
      expect(screen.getByTestId('delete-confirm-dialog')).toBeInTheDocument();
    });

    it('calls onDeleteAccount when confirmed', async () => {
      const onDeleteAccount = vi.fn().mockResolvedValue(undefined);
      render(<SettingsPage onDeleteAccount={onDeleteAccount} />);
      fireEvent.click(screen.getByTestId('tab-security'));
      fireEvent.click(screen.getByTestId('delete-account-btn'));
      fireEvent.click(screen.getByTestId('confirm-delete'));

      expect(onDeleteAccount).toHaveBeenCalled();
    });
  });

  describe('Notifications Tab', () => {
    it('displays notification options', () => {
      render(<SettingsPage settings={defaultSettings} />);
      fireEvent.click(screen.getByTestId('tab-notifications'));
      
      expect(screen.getByTestId('notif-email')).toBeInTheDocument();
      expect(screen.getByTestId('notif-push')).toBeInTheDocument();
      expect(screen.getByTestId('notif-desktop')).toBeInTheDocument();
    });

    it('shows current notification settings', () => {
      render(<SettingsPage settings={defaultSettings} />);
      fireEvent.click(screen.getByTestId('tab-notifications'));
      
      expect(screen.getByTestId('notif-email')).toBeChecked();
      expect(screen.getByTestId('notif-push')).toBeChecked();
      expect(screen.getByTestId('notif-desktop')).toBeChecked();
    });

    it('calls onUpdateSettings when notification is toggled', async () => {
      const onUpdateSettings = vi.fn().mockResolvedValue(undefined);
      render(<SettingsPage settings={defaultSettings} onUpdateSettings={onUpdateSettings} />);
      fireEvent.click(screen.getByTestId('tab-notifications'));
      
      fireEvent.click(screen.getByTestId('notif-email'));

      expect(onUpdateSettings).toHaveBeenCalled();
    });
  });
});
