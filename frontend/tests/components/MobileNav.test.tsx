import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  usePathname: () => '/chat',
}));

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href, onClick }: { children: React.ReactNode; href: string; onClick?: () => void }) => (
    <a href={href} onClick={onClick}>{children}</a>
  ),
}));

// Mock ThemeToggle
vi.mock('@/components/ui/theme-toggle', () => ({
  ThemeToggle: ({ className }: { className?: string }) => (
    <button className={className} data-testid="theme-toggle">Theme</button>
  ),
}));

// Mock auth store
const mockLogout = vi.fn();
const mockUser = {
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  full_name: 'Test User',
  role: 'user',
  is_verified: true,
};

let mockIsAuthenticated = true;

vi.mock('@/store/auth', () => ({
  useAuthStore: () => ({
    isAuthenticated: mockIsAuthenticated,
    user: mockIsAuthenticated ? mockUser : null,
    logout: mockLogout,
  }),
}));

// Import after mocks
import { MobileNav, Header } from '@/components/ui/mobile-nav';

describe('MobileNav', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
    document.body.style.overflow = '';
  });

  it('renders hamburger button', () => {
    render(<MobileNav />);
    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
  });

  it('opens menu when hamburger clicked', () => {
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('NexusAI')).toBeInTheDocument();
  });

  it('shows navigation links when open', () => {
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
  });

  it('shows user info when authenticated', () => {
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });

  it('shows logout button when authenticated', () => {
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Log out')).toBeInTheDocument();
  });

  it('calls logout when logout button clicked', () => {
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    fireEvent.click(screen.getByText('Log out'));
    
    expect(mockLogout).toHaveBeenCalled();
  });

  it('shows login/signup buttons when not authenticated', () => {
    mockIsAuthenticated = false;
    
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Log in')).toBeInTheDocument();
    expect(screen.getByText('Sign up')).toBeInTheDocument();
  });

  it('prevents body scroll when open', () => {
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(document.body.style.overflow).toBe('hidden');
  });

  it('renders navigation with Chat link', () => {
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    // The Chat link should be present in the menu
    const chatLink = screen.getByText('Chat').closest('a');
    expect(chatLink).toBeInTheDocument();
    expect(chatLink).toHaveAttribute('href', '/chat');
  });

  it('shows secondary navigation items', () => {
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Pricing')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('hides auth-required links when not authenticated', () => {
    mockIsAuthenticated = false;
    
    render(<MobileNav />);
    
    fireEvent.click(screen.getByRole('button', { name: /open menu/i }));
    
    // Settings requires auth, so it should not be visible
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
    // But Pricing doesn't require auth
    expect(screen.getByText('Pricing')).toBeInTheDocument();
  });
});

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
  });

  it('renders header with logo', () => {
    render(<Header />);
    expect(screen.getAllByText('NexusAI').length).toBeGreaterThan(0);
  });

  it('renders mobile nav by default', () => {
    render(<Header />);
    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
  });

  it('hides mobile nav when showNav is false', () => {
    render(<Header showNav={false} />);
    expect(screen.queryByRole('button', { name: /open menu/i })).not.toBeInTheDocument();
  });

  it('renders desktop navigation links', () => {
    render(<Header />);
    
    // Desktop nav links (these are visible on md screens and up)
    const desktopNav = document.querySelector('.hidden.md\\:flex');
    expect(desktopNav).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Header className="custom-header" />);
    
    const header = document.querySelector('header');
    expect(header).toHaveClass('custom-header');
  });

  it('shows login/signup when not authenticated', () => {
    mockIsAuthenticated = false;
    
    render(<Header />);
    
    // These are in the desktop nav (hidden on mobile) - there may be multiple
    expect(screen.getAllByText('Log in').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Sign up').length).toBeGreaterThan(0);
  });

  it('shows user icon when authenticated', () => {
    render(<Header />);
    
    // The user icon button should be present
    const settingsLink = document.querySelector('a[href="/settings"]');
    expect(settingsLink).toBeInTheDocument();
  });

  it('includes theme toggle', () => {
    render(<Header />);
    // There may be multiple theme toggles (mobile nav and desktop)
    const themeToggles = screen.getAllByTestId('theme-toggle');
    expect(themeToggles.length).toBeGreaterThan(0);
  });
});
