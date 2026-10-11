'use client';

/**
 * Admin Layout
 *
 * Provides navigation and structure for admin pages.
 * Includes role-based access control.
 */

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  Users,
  Building2,
  Settings,
  Shield,
  BarChart3,
  ChevronLeft,
  Menu,
  X,
  LogOut,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { DoAideLogo } from '@/components/ui/doaide-logo';
import { useAuthStore } from '@/store/auth';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  description?: string;
}

const adminNavItems: NavItem[] = [
  {
    label: 'Users',
    href: '/admin/users',
    icon: <Users className="h-5 w-5" />,
    description: 'Manage user accounts',
  },
  {
    label: 'Organizations',
    href: '/admin/organizations',
    icon: <Building2 className="h-5 w-5" />,
    description: 'Manage organizations',
  },
  {
    label: 'Trials',
    href: '/admin/trials',
    icon: <Clock className="h-5 w-5" />,
    description: 'Manage trial periods',
  },
  {
    label: 'Roles & Permissions',
    href: '/admin/roles',
    icon: <Shield className="h-5 w-5" />,
    description: 'Configure access control',
  },
  {
    label: 'Analytics',
    href: '/admin/analytics',
    icon: <BarChart3 className="h-5 w-5" />,
    description: 'Platform usage statistics',
  },
  {
    label: 'Settings',
    href: '/admin/settings',
    icon: <Settings className="h-5 w-5" />,
    description: 'System configuration',
  },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuthStore();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Check if user has admin access
  useEffect(() => {
    // Give store time to hydrate from localStorage
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/login?redirect=/admin');
      } else if (user && user.role !== 'org_admin' && user.role !== 'staff_admin') {
        router.push('/');
      }
    }
  }, [isLoading, isAuthenticated, user, router]);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const isAuthorized = isAuthenticated && user && (user.role === 'org_admin' || user.role === 'staff_admin');

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center animate-pulse">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <p className="text-sm text-muted-foreground">Verifying access...</p>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-background border-b px-4 py-3">
        <div className="flex items-center justify-between">
          <Link href="/admin" className="flex items-center gap-2">
            <DoAideLogo size={20} />
            <span className="font-semibold">Admin</span>
          </Link>
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-2 hover:bg-muted rounded-md"
            aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
          >
            {isMobileMenuOpen ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-40 bg-background/80 backdrop-blur-sm" onClick={() => setIsMobileMenuOpen(false)} aria-hidden="true" />
      )}

      {/* Mobile Sidebar */}
      <aside
        className={cn(
          'lg:hidden fixed top-14 left-0 bottom-0 z-40 w-64 bg-background border-r transform transition-transform duration-200',
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <nav className="p-4 space-y-1" aria-label="Admin navigation">
          {adminNavItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setIsMobileMenuOpen(false)}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                pathname === item.href || pathname.startsWith(item.href + '/')
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              )}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>

      {/* Desktop Sidebar */}
      <aside
        className={cn(
          'hidden lg:flex fixed top-0 left-0 bottom-0 z-40 flex-col bg-background border-r transition-all duration-200',
          isSidebarOpen ? 'w-64' : 'w-16'
        )}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <Link
            href="/admin"
            className={cn(
              'flex items-center gap-2 transition-opacity',
              !isSidebarOpen && 'opacity-0 pointer-events-none'
            )}
          >
            <DoAideLogo size={20} />
            <span className="font-semibold">GSTIndia Admin</span>
          </Link>
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-1.5 hover:bg-muted rounded-md"
            aria-label={isSidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <ChevronLeft className={cn('h-4 w-4 transition-transform', !isSidebarOpen && 'rotate-180')} aria-hidden="true" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {adminNavItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              title={!isSidebarOpen ? item.label : undefined}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                pathname === item.href || pathname.startsWith(item.href + '/')
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted',
                !isSidebarOpen && 'justify-center px-2'
              )}
            >
              {item.icon}
              {isSidebarOpen && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3 border-t">
          <Link
            href="/"
            className={cn(
              'flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground',
              !isSidebarOpen && 'justify-center px-2'
            )}
          >
            <ChevronLeft className="h-5 w-5" />
            {isSidebarOpen && <span>Back to App</span>}
          </Link>
          <button
            onClick={handleLogout}
            className={cn(
              'flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-destructive/10 hover:text-destructive transition-colors w-full text-left',
              !isSidebarOpen && 'justify-center px-2'
            )}
          >
            <LogOut className="h-5 w-5" />
            {isSidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main
        className={cn(
          'min-h-screen transition-all duration-200 pt-14 lg:pt-0',
          isSidebarOpen ? 'lg:pl-64' : 'lg:pl-16'
        )}
      >
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
