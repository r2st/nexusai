import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeToggle, ThemeSelect } from '@/components/ui/theme-toggle';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock matchMedia
const mockMatchMedia = vi.fn().mockImplementation((query) => ({
  matches: query === '(prefers-color-scheme: dark)',
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}));

Object.defineProperty(window, 'matchMedia', {
  value: mockMatchMedia,
});

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    document.documentElement.classList.remove('light', 'dark');
  });

  afterEach(() => {
    document.documentElement.classList.remove('light', 'dark');
  });

  it('renders a button', () => {
    render(<ThemeToggle />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('has accessible label', async () => {
    render(<ThemeToggle />);
    
    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label');
    });
  });

  it('cycles through themes when clicked', async () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');

    // Wait for mount
    await waitFor(() => {
      expect(button).toHaveAttribute('aria-label');
    });

    // Initial state is system
    expect(button.getAttribute('aria-label')).toContain('system');

    // Click to change to light
    fireEvent.click(button);
    await waitFor(() => {
      expect(button.getAttribute('aria-label')).toContain('light');
    });

    // Click to change to dark
    fireEvent.click(button);
    await waitFor(() => {
      expect(button.getAttribute('aria-label')).toContain('dark');
    });

    // Click to change back to system
    fireEvent.click(button);
    await waitFor(() => {
      expect(button.getAttribute('aria-label')).toContain('system');
    });
  });

  it('persists theme to localStorage', async () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');

    await waitFor(() => {
      expect(button).toHaveAttribute('aria-label');
    });

    // Click to light
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light');
    });
  });

  it('loads theme from localStorage on mount', async () => {
    localStorageMock.getItem.mockReturnValue('dark');
    
    render(<ThemeToggle />);
    
    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button.getAttribute('aria-label')).toContain('dark');
    });
  });

  it('applies custom className', () => {
    render(<ThemeToggle className="custom-class" />);
    expect(screen.getByRole('button')).toHaveClass('custom-class');
  });

  it('adds theme class to document element', async () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');

    await waitFor(() => {
      expect(button).toHaveAttribute('aria-label');
    });

    // Click to change theme
    fireEvent.click(button);
    
    await waitFor(() => {
      // After clicking, theme should change (either light or dark class should be present)
      const hasThemeClass = document.documentElement.classList.contains('light') || 
                           document.documentElement.classList.contains('dark');
      expect(hasThemeClass).toBe(true);
    });
  });
});

describe('ThemeSelect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    document.documentElement.classList.remove('light', 'dark');
  });

  afterEach(() => {
    document.documentElement.classList.remove('light', 'dark');
  });

  it('renders all theme options', async () => {
    render(<ThemeSelect />);
    
    await waitFor(() => {
      expect(screen.getByText('Light')).toBeInTheDocument();
      expect(screen.getByText('Dark')).toBeInTheDocument();
      expect(screen.getByText('System')).toBeInTheDocument();
    });
  });

  it('highlights current theme', async () => {
    localStorageMock.getItem.mockReturnValue('dark');
    
    render(<ThemeSelect />);
    
    await waitFor(() => {
      const darkButton = screen.getByText('Dark').closest('button');
      expect(darkButton).toHaveClass('bg-background');
    });
  });

  it('changes theme when option clicked', async () => {
    render(<ThemeSelect />);
    
    await waitFor(() => {
      expect(screen.getByText('Light')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Light'));
    
    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light');
    });
  });

  it('applies custom className', async () => {
    render(<ThemeSelect className="custom-class" />);
    
    await waitFor(() => {
      // The custom class is applied to the outer container div
      const container = document.querySelector('.custom-class');
      expect(container).toBeInTheDocument();
    });
  });

  it('removes theme from localStorage when system is selected', async () => {
    localStorageMock.getItem.mockReturnValue('light');
    
    render(<ThemeSelect />);
    
    await waitFor(() => {
      expect(screen.getByText('System')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('System'));
    
    await waitFor(() => {
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('theme');
    });
  });
});
