/**
 * Tests for SetupLauncher Component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { SetupLauncher, PluginCard } from '@/components/setup-assistant/setup-assistant';

// Mock the API
vi.mock('@/lib/api', () => ({
  setupAssistantApi: {
    listPlugins: vi.fn(),
  },
}));

import { setupAssistantApi } from '@/lib/api';

const mockPlugins = [
  {
    plugin_type: 'github',
    display_name: 'GitHub',
    description: 'Connect to GitHub repositories',
    icon: '🐙',
    required_fields: ['token'],
    optional_fields: ['endpoint'],
    auth_type: 'token',
    endpoint_required: false,
    scopes_supported: ['repos', 'issues', 'pull_requests'],
  },
  {
    plugin_type: 'jira',
    display_name: 'Jira',
    description: 'Connect to Jira for issue tracking',
    icon: '📋',
    required_fields: ['token', 'endpoint'],
    optional_fields: [],
    auth_type: 'token',
    endpoint_required: true,
    scopes_supported: ['boards', 'issues'],
  },
];

describe('SetupLauncher', () => {
  const mockOnStartSetup = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (setupAssistantApi.listPlugins as ReturnType<typeof vi.fn>).mockResolvedValue(mockPlugins);
  });

  it('renders Get Started section', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      expect(screen.getByText('Get Started')).toBeInTheDocument();
    });
  });

  it('renders quick action buttons', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);

    await waitFor(() => {
      expect(screen.getByText('Start Onboarding')).toBeInTheDocument();
      expect(screen.getByText('Create Project')).toBeInTheDocument();
      expect(screen.getByText('Configure Pipeline')).toBeInTheDocument();
      expect(screen.getByText('Add Connection')).toBeInTheDocument();
    });
  });

  it('calls onStartSetup with "onboarding" when Start Onboarding clicked', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      expect(screen.getByText('Start Onboarding')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Start Onboarding'));
    expect(mockOnStartSetup).toHaveBeenCalledWith('onboarding');
  });

  it('calls onStartSetup with "project" when Create Project clicked', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      expect(screen.getByText('Create Project')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Project'));
    expect(mockOnStartSetup).toHaveBeenCalledWith('project');
  });

  it('calls onStartSetup with "pipeline" when Configure Pipeline clicked', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      expect(screen.getByText('Configure Pipeline')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Configure Pipeline'));
    expect(mockOnStartSetup).toHaveBeenCalledWith('pipeline');
  });

  it('calls onStartSetup with "connection" when Add Connection clicked', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      expect(screen.getByText('Add Connection')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add Connection'));
    expect(mockOnStartSetup).toHaveBeenCalledWith('connection');
  });

  it('calls onStartSetup with "onboarding" when Start Onboarding clicked', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);

    await waitFor(() => {
      expect(screen.getByText('Start Onboarding')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Start Onboarding'));
    expect(mockOnStartSetup).toHaveBeenCalledWith('onboarding');
  });

  it('renders Quick Connect section', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      expect(screen.getByText('Quick Connect')).toBeInTheDocument();
    });
  });

  it('loads plugins from API', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      expect(setupAssistantApi.listPlugins).toHaveBeenCalled();
    });
  });

  it('displays plugin cards after loading', async () => {
    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      expect(screen.getByText('GitHub')).toBeInTheDocument();
      expect(screen.getByText('Jira')).toBeInTheDocument();
    });
  });

  it('uses default plugins when API fails', async () => {
    (setupAssistantApi.listPlugins as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('401 Unauthorized')
    );

    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      // Should still show default plugins
      expect(screen.getByText('GitHub')).toBeInTheDocument();
    });
  });

  it('uses default plugins when API returns empty', async () => {
    (setupAssistantApi.listPlugins as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<SetupLauncher onStartSetup={mockOnStartSetup} />);
    
    await waitFor(() => {
      // Should still show default plugins
      expect(screen.getByText('GitHub')).toBeInTheDocument();
    });
  });
});

describe('PluginCard', () => {
  const mockPlugin = {
    plugin_type: 'github',
    display_name: 'GitHub',
    description: 'Connect to GitHub repositories for code metrics',
    icon: '🐙',
    required_fields: ['token'],
    optional_fields: ['endpoint'],
    auth_type: 'token',
    endpoint_required: false,
    scopes_supported: ['repos', 'issues', 'pull_requests', 'commits'],
  };

  it('renders plugin information', () => {
    render(<PluginCard plugin={mockPlugin} onClick={() => {}} />);
    
    expect(screen.getByText('GitHub')).toBeInTheDocument();
    expect(screen.getByText('Connect to GitHub repositories for code metrics')).toBeInTheDocument();
    expect(screen.getByText('🐙')).toBeInTheDocument();
  });

  it('renders scope badges (max 3)', () => {
    render(<PluginCard plugin={mockPlugin} onClick={() => {}} />);
    
    expect(screen.getByText('repos')).toBeInTheDocument();
    expect(screen.getByText('issues')).toBeInTheDocument();
    expect(screen.getByText('pull_requests')).toBeInTheDocument();
    // 'commits' should not be shown (4th scope)
    expect(screen.queryByText('commits')).not.toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<PluginCard plugin={mockPlugin} onClick={handleClick} />);
    
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalled();
  });
});
