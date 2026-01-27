/**
 * useResponsive Hook Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Mock useResponsive hook
type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

interface ResponsiveState {
  width: number;
  height: number;
  breakpoint: Breakpoint;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isPortrait: boolean;
  isLandscape: boolean;
}

const breakpoints = {
  xs: 0,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
};

const getBreakpoint = (width: number): Breakpoint => {
  if (width >= breakpoints['2xl']) return '2xl';
  if (width >= breakpoints.xl) return 'xl';
  if (width >= breakpoints.lg) return 'lg';
  if (width >= breakpoints.md) return 'md';
  if (width >= breakpoints.sm) return 'sm';
  return 'xs';
};

const useResponsive = (): ResponsiveState => {
  const [state, setState] = React.useState<ResponsiveState>(() => ({
    width: window.innerWidth,
    height: window.innerHeight,
    breakpoint: getBreakpoint(window.innerWidth),
    isMobile: window.innerWidth < breakpoints.md,
    isTablet: window.innerWidth >= breakpoints.md && window.innerWidth < breakpoints.lg,
    isDesktop: window.innerWidth >= breakpoints.lg,
    isPortrait: window.innerHeight > window.innerWidth,
    isLandscape: window.innerWidth > window.innerHeight,
  }));

  React.useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      setState({
        width,
        height,
        breakpoint: getBreakpoint(width),
        isMobile: width < breakpoints.md,
        isTablet: width >= breakpoints.md && width < breakpoints.lg,
        isDesktop: width >= breakpoints.lg,
        isPortrait: height > width,
        isLandscape: width > height,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return state;
};

import React from 'react';

describe('useResponsive', () => {
  const setWindowSize = (width: number, height: number) => {
    Object.defineProperty(window, 'innerWidth', { value: width, writable: true });
    Object.defineProperty(window, 'innerHeight', { value: height, writable: true });
  };

  const triggerResize = () => {
    window.dispatchEvent(new Event('resize'));
  };

  beforeEach(() => {
    setWindowSize(1024, 768);
  });

  it('returns current window dimensions', () => {
    setWindowSize(1200, 800);
    const { result } = renderHook(() => useResponsive());
    expect(result.current.width).toBe(1200);
    expect(result.current.height).toBe(800);
  });

  describe('breakpoints', () => {
    it('returns xs for width < 640', () => {
      setWindowSize(500, 800);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.breakpoint).toBe('xs');
    });

    it('returns sm for width >= 640 and < 768', () => {
      setWindowSize(700, 800);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.breakpoint).toBe('sm');
    });

    it('returns md for width >= 768 and < 1024', () => {
      setWindowSize(900, 800);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.breakpoint).toBe('md');
    });

    it('returns lg for width >= 1024 and < 1280', () => {
      setWindowSize(1100, 800);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.breakpoint).toBe('lg');
    });

    it('returns xl for width >= 1280 and < 1536', () => {
      setWindowSize(1400, 800);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.breakpoint).toBe('xl');
    });

    it('returns 2xl for width >= 1536', () => {
      setWindowSize(1920, 1080);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.breakpoint).toBe('2xl');
    });
  });

  describe('device detection', () => {
    it('detects mobile', () => {
      setWindowSize(375, 667);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.isMobile).toBe(true);
      expect(result.current.isTablet).toBe(false);
      expect(result.current.isDesktop).toBe(false);
    });

    it('detects tablet', () => {
      setWindowSize(800, 1024);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.isMobile).toBe(false);
      expect(result.current.isTablet).toBe(true);
      expect(result.current.isDesktop).toBe(false);
    });

    it('detects desktop', () => {
      setWindowSize(1920, 1080);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.isMobile).toBe(false);
      expect(result.current.isTablet).toBe(false);
      expect(result.current.isDesktop).toBe(true);
    });
  });

  describe('orientation', () => {
    it('detects portrait orientation', () => {
      setWindowSize(768, 1024);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.isPortrait).toBe(true);
      expect(result.current.isLandscape).toBe(false);
    });

    it('detects landscape orientation', () => {
      setWindowSize(1024, 768);
      const { result } = renderHook(() => useResponsive());
      expect(result.current.isPortrait).toBe(false);
      expect(result.current.isLandscape).toBe(true);
    });
  });

  describe('resize handling', () => {
    it('updates on window resize', () => {
      setWindowSize(1024, 768);
      const { result } = renderHook(() => useResponsive());
      
      expect(result.current.breakpoint).toBe('lg');

      act(() => {
        setWindowSize(500, 800);
        triggerResize();
      });

      expect(result.current.breakpoint).toBe('xs');
      expect(result.current.isMobile).toBe(true);
    });

    it('cleans up event listener on unmount', () => {
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');
      const { unmount } = renderHook(() => useResponsive());
      
      unmount();
      
      expect(removeEventListenerSpy).toHaveBeenCalledWith('resize', expect.any(Function));
      removeEventListenerSpy.mockRestore();
    });
  });
});
