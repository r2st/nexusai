'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Menu,
  X,
  MessageSquare,
  FileText,
  BarChart3,
  Bot,
  Settings,
  LogOut,
  Sparkles,
  User,
  Activity,
  Zap,
  CreditCard,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  icon: typeof MessageSquare;
  requireAuth?: boolean;
}

const mainNavItems: NavItem[] = [
  { href: '/chat', label: 'Chat', icon: MessageSquare, requireAuth: true },
  { href: '/documents', label: 'Documents', icon: FileText, requireAuth: true },
  { href: '/agents', label: 'Agents', icon: Bot, requireAuth: true },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/devops', label: 'DevOps', icon: Activity, requireAuth: true },
  { href: '/knowledge-graph', label: 'Knowledge Graph', icon: Zap, requireAuth: true },
];

const secondaryNavItems: NavItem[] = [
  { href: '/pricing', label: 'Pricing', icon: CreditCard },
  { href: '/settings', label: 'Settings', icon: Settings, requireAuth: true },
];

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();
  const { isAuthenticated, user, logout } = useAuthStore();

  // Close menu on route change
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  // Prevent body scroll when menu is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleLogout = () => {
    logout();
    setIsOpen(false);
  };

  return (
    <>
      {/* Hamburger Button */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? 'Close menu' : 'Open menu'}
        aria-expanded={isOpen}
      >
        {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Menu */}
      <div
        role="dialog"
        aria-modal={isOpen}
        aria-label="Navigation menu"
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-72 bg-background border-r transform transition-transform duration-300 ease-in-out md:hidden',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          <Link href="/" className="flex items-center gap-2" onClick={() => setIsOpen(false)}>
            <Sparkles className="h-6 w-6 text-primary" aria-hidden="true" />
            <span className="text-xl font-bold">NexusAI</span>
          </Link>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)} aria-label="Close menu">
              <X className="h-5 w-5" aria-hidden="true" />
            </Button>
          </div>
        </div>

        {/* User Info */}
        {isAuthenticated && user && (
          <div className="border-b p-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">
                {user.full_name?.charAt(0) || user.email?.charAt(0) || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{user.full_name || 'User'}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4">
          <div className="space-y-1">
            {mainNavItems.map((item) => {
              if (item.requireAuth && !isAuthenticated) return null;
              const Icon = item.icon;
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsOpen(false)}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </div>

          <hr className="my-4" />

          <div className="space-y-1">
            {secondaryNavItems.map((item) => {
              if (item.requireAuth && !isAuthenticated) return null;
              const Icon = item.icon;
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsOpen(false)}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Footer */}
        <div className="border-t p-4">
          {isAuthenticated ? (
            <Button
              variant="ghost"
              className="w-full justify-start text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={handleLogout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </Button>
          ) : (
            <div className="space-y-2">
              <Link href="/login" onClick={() => setIsOpen(false)}>
                <Button variant="outline" className="w-full">
                  Log in
                </Button>
              </Link>
              <Link href="/register" onClick={() => setIsOpen(false)}>
                <Button className="w-full">
                  Sign up
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

/**
 * Header component with mobile navigation
 */
interface HeaderProps {
  showNav?: boolean;
  className?: string;
}

export function Header({ showNav = true, className }: HeaderProps) {
  const { isAuthenticated } = useAuthStore();

  return (
    <header className={cn('border-b bg-background/80 backdrop-blur-sm sticky top-0 z-30', className)}>
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* Left: Logo + Mobile Nav */}
        <div className="flex items-center gap-2">
          {showNav && <MobileNav />}
          <Link href="/" className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold hidden sm:inline">NexusAI</span>
          </Link>
        </div>

        {/* Center: Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-6">
          <Link href="/chat" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            Chat
          </Link>
          <Link href="/documents" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            Documents
          </Link>
          <Link href="/agents" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            Agents
          </Link>
          <Link href="/analytics" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            Analytics
          </Link>
        </nav>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <ThemeToggle className="hidden sm:flex" />
          {isAuthenticated ? (
            <>
              <Link href="/settings" className="hidden sm:block">
                <Button variant="ghost" size="icon" aria-label="Settings">
                  <User className="h-4 w-4" aria-hidden="true" />
                </Button>
              </Link>
            </>
          ) : (
            <div className="hidden sm:flex items-center gap-2">
              <Link href="/login">
                <Button variant="ghost" size="sm">
                  Log in
                </Button>
              </Link>
              <Link href="/register">
                <Button size="sm">
                  Sign up
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
