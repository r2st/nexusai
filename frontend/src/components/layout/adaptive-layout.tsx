'use client';

import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { usePreferencesStore, useUserMode } from '@/store/preferences';

interface AdaptiveLayoutProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Adaptive layout that adjusts based on user mode and preferences.
 * 
 * Applies global styles based on:
 * - User mode (technical/non-technical)
 * - Font size preference
 * - Reduce motion preference
 * - High contrast preference
 */
export function AdaptiveLayout({ children, className }: AdaptiveLayoutProps) {
  const userMode = useUserMode();
  const { fontSize, reduceMotion, highContrast, theme } = usePreferencesStore();

  // Apply accessibility preferences to document
  useEffect(() => {
    const root = document.documentElement;

    // Font size
    const fontSizeMap = {
      small: '14px',
      medium: '16px',
      large: '18px',
    };
    root.style.fontSize = fontSizeMap[fontSize];

    // Reduce motion
    if (reduceMotion) {
      root.classList.add('reduce-motion');
    } else {
      root.classList.remove('reduce-motion');
    }

    // High contrast
    if (highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }

    // User mode class for CSS targeting
    root.setAttribute('data-user-mode', userMode);

    return () => {
      root.style.fontSize = '';
      root.classList.remove('reduce-motion', 'high-contrast');
      root.removeAttribute('data-user-mode');
    };
  }, [fontSize, reduceMotion, highContrast, userMode]);

  return (
    <div
      className={cn(
        'min-h-screen bg-background text-foreground',
        // Simplified UI for non-technical users
        userMode === 'non-technical' && 'non-tech-mode',
        className
      )}
      data-mode={userMode}
    >
      {children}
    </div>
  );
}

/**
 * Component that only renders for technical users
 */
export function TechnicalOnly({ children }: { children: React.ReactNode }) {
  const userMode = useUserMode();

  if (userMode !== 'technical') {
    return null;
  }

  return <>{children}</>;
}

/**
 * Component that renders different content based on user mode
 */
export function AdaptiveContent({
  technical,
  nonTechnical,
}: {
  technical: React.ReactNode;
  nonTechnical: React.ReactNode;
}) {
  const userMode = useUserMode();

  return <>{userMode === 'technical' ? technical : nonTechnical}</>;
}

/**
 * Hook to check if we should show simplified UI
 */
export function useSimplifiedUI(): boolean {
  const userMode = useUserMode();
  return userMode === 'non-technical';
}

export default AdaptiveLayout;
