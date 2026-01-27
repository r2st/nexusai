'use client';

import { useState, useEffect, useCallback } from 'react';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface ResponsiveState {
  breakpoint: Breakpoint;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  width: number;
  height: number;
}

export interface UseResponsiveOptions {
  debounceMs?: number;
}

// -----------------------------------------------------------------------------
// Breakpoint Configuration (matches Tailwind defaults)
// -----------------------------------------------------------------------------

const BREAKPOINTS: Record<Breakpoint, number> = {
  xs: 0,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
};

// -----------------------------------------------------------------------------
// Utility Functions
// -----------------------------------------------------------------------------

function getBreakpoint(width: number): Breakpoint {
  if (width >= BREAKPOINTS['2xl']) return '2xl';
  if (width >= BREAKPOINTS.xl) return 'xl';
  if (width >= BREAKPOINTS.lg) return 'lg';
  if (width >= BREAKPOINTS.md) return 'md';
  if (width >= BREAKPOINTS.sm) return 'sm';
  return 'xs';
}

function debounce<T extends (...args: unknown[]) => void>(
  fn: T,
  ms: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => fn(...args), ms);
  };
}

// -----------------------------------------------------------------------------
// useResponsive Hook
// -----------------------------------------------------------------------------

export function useResponsive(options: UseResponsiveOptions = {}): ResponsiveState {
  const { debounceMs = 100 } = options;

  const [state, setState] = useState<ResponsiveState>(() => {
    if (typeof window === 'undefined') {
      return {
        breakpoint: 'md',
        isMobile: false,
        isTablet: false,
        isDesktop: true,
        width: 1024,
        height: 768,
      };
    }

    const width = window.innerWidth;
    const height = window.innerHeight;
    const breakpoint = getBreakpoint(width);

    return {
      breakpoint,
      isMobile: width < BREAKPOINTS.md,
      isTablet: width >= BREAKPOINTS.md && width < BREAKPOINTS.lg,
      isDesktop: width >= BREAKPOINTS.lg,
      width,
      height,
    };
  });

  useEffect(() => {
    const handleResize = debounce(() => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      const breakpoint = getBreakpoint(width);

      setState({
        breakpoint,
        isMobile: width < BREAKPOINTS.md,
        isTablet: width >= BREAKPOINTS.md && width < BREAKPOINTS.lg,
        isDesktop: width >= BREAKPOINTS.lg,
        width,
        height,
      });
    }, debounceMs);

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [debounceMs]);

  return state;
}

// -----------------------------------------------------------------------------
// useMediaQuery Hook
// -----------------------------------------------------------------------------

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

// -----------------------------------------------------------------------------
// useBreakpoint Hook
// -----------------------------------------------------------------------------

export function useBreakpoint(breakpoint: Breakpoint): boolean {
  return useMediaQuery(`(min-width: ${BREAKPOINTS[breakpoint]}px)`);
}

// -----------------------------------------------------------------------------
// useSidebar Hook (for responsive sidebar management)
// -----------------------------------------------------------------------------

export interface UseSidebarReturn {
  isOpen: boolean;
  isMobile: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

export function useSidebar(): UseSidebarReturn {
  const { isMobile } = useResponsive();
  const [isOpen, setIsOpen] = useState(!isMobile);

  // Close sidebar on mobile when navigating
  useEffect(() => {
    if (isMobile) {
      setIsOpen(false);
    } else {
      setIsOpen(true);
    }
  }, [isMobile]);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen(prev => !prev), []);

  return { isOpen, isMobile, open, close, toggle };
}

// -----------------------------------------------------------------------------
// useContextPanel Hook (for responsive context panel)
// -----------------------------------------------------------------------------

export interface UseContextPanelReturn {
  isOpen: boolean;
  isCollapsed: boolean;
  variant: 'panel' | 'drawer' | 'sheet';
  open: () => void;
  close: () => void;
  toggle: () => void;
  collapse: () => void;
  expand: () => void;
}

export function useContextPanel(): UseContextPanelReturn {
  const { isMobile, isTablet, isDesktop } = useResponsive();
  const [isOpen, setIsOpen] = useState(isDesktop);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Determine variant based on screen size
  const variant: 'panel' | 'drawer' | 'sheet' = isMobile
    ? 'sheet'
    : isTablet
    ? 'drawer'
    : 'panel';

  // Auto-collapse on tablet, auto-close on mobile
  useEffect(() => {
    if (isMobile) {
      setIsOpen(false);
      setIsCollapsed(false);
    } else if (isTablet) {
      setIsCollapsed(true);
    } else {
      setIsCollapsed(false);
      setIsOpen(true);
    }
  }, [isMobile, isTablet]);

  const open = useCallback(() => {
    setIsOpen(true);
    setIsCollapsed(false);
  }, []);

  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen(prev => !prev), []);
  const collapse = useCallback(() => setIsCollapsed(true), []);
  const expand = useCallback(() => setIsCollapsed(false), []);

  return {
    isOpen,
    isCollapsed,
    variant,
    open,
    close,
    toggle,
    collapse,
    expand,
  };
}

// -----------------------------------------------------------------------------
// useTouchDevice Hook
// -----------------------------------------------------------------------------

export function useTouchDevice(): boolean {
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    const checkTouch = () => {
      setIsTouch(
        'ontouchstart' in window ||
        navigator.maxTouchPoints > 0
      );
    };

    checkTouch();
  }, []);

  return isTouch;
}

// -----------------------------------------------------------------------------
// useScrollLock Hook (for mobile modals/drawers)
// -----------------------------------------------------------------------------

export function useScrollLock(locked: boolean): void {
  useEffect(() => {
    if (!locked) return;

    const originalStyle = window.getComputedStyle(document.body).overflow;
    const originalPaddingRight = window.getComputedStyle(document.body).paddingRight;

    // Calculate scrollbar width
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;

    // Lock scroll
    document.body.style.overflow = 'hidden';
    document.body.style.paddingRight = `${scrollbarWidth}px`;

    return () => {
      document.body.style.overflow = originalStyle;
      document.body.style.paddingRight = originalPaddingRight;
    };
  }, [locked]);
}

// -----------------------------------------------------------------------------
// Prefers Reduced Motion Hook
// -----------------------------------------------------------------------------

export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
}

// -----------------------------------------------------------------------------
// Dark Mode Hook
// -----------------------------------------------------------------------------

export function usePrefersDarkMode(): boolean {
  return useMediaQuery('(prefers-color-scheme: dark)');
}

export default useResponsive;
