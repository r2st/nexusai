/**
 * User preferences store for role-based UI adaptations.
 * 
 * Manages user settings that affect the UI experience:
 * - Technical vs non-technical mode
 * - Theme preferences
 * - Accessibility settings
 * - Chat behavior preferences
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type UserMode = 'technical' | 'non-technical' | 'auto';
export type ThemeMode = 'light' | 'dark' | 'system';
export type ChatDensity = 'compact' | 'comfortable' | 'spacious';
export type SuggestionStyle = 'chips' | 'list' | 'cards' | 'hidden';

interface PreferencesState {
  // User mode (affects UI complexity)
  userMode: UserMode;
  detectedMode: 'technical' | 'non-technical'; // Auto-detected based on usage

  // Theme
  theme: ThemeMode;
  
  // Chat preferences
  chatDensity: ChatDensity;
  showTypingIndicator: boolean;
  showSuggestions: boolean;
  suggestionStyle: SuggestionStyle;
  enableSoundEffects: boolean;
  enableAnimations: boolean;
  showCodeLineNumbers: boolean;
  autoScroll: boolean;

  // Accessibility
  reduceMotion: boolean;
  highContrast: boolean;
  fontSize: 'small' | 'medium' | 'large';
  
  // Advanced features (technical users)
  showAdvancedFeatures: boolean;
  enableKeyboardShortcuts: boolean;
  showDebugInfo: boolean;
  
  // Onboarding
  hasCompletedOnboarding: boolean;
  hasSeenWelcome: boolean;
  dismissedTips: string[];

  // Actions
  setUserMode: (mode: UserMode) => void;
  setTheme: (theme: ThemeMode) => void;
  setChatDensity: (density: ChatDensity) => void;
  setShowSuggestions: (show: boolean) => void;
  setSuggestionStyle: (style: SuggestionStyle) => void;
  setShowAdvancedFeatures: (show: boolean) => void;
  setReduceMotion: (reduce: boolean) => void;
  setHighContrast: (high: boolean) => void;
  setFontSize: (size: 'small' | 'medium' | 'large') => void;
  completeOnboarding: () => void;
  markWelcomeSeen: () => void;
  dismissTip: (tipId: string) => void;
  resetPreferences: () => void;

  // Computed
  getEffectiveMode: () => 'technical' | 'non-technical';
  shouldShowFeature: (featureLevel: 'basic' | 'intermediate' | 'advanced') => boolean;
}

const DEFAULT_PREFERENCES = {
  userMode: 'auto' as UserMode,
  detectedMode: 'technical' as const,
  theme: 'system' as ThemeMode,
  chatDensity: 'comfortable' as ChatDensity,
  showTypingIndicator: true,
  showSuggestions: true,
  suggestionStyle: 'chips' as SuggestionStyle,
  enableSoundEffects: false,
  enableAnimations: true,
  showCodeLineNumbers: true,
  autoScroll: true,
  reduceMotion: false,
  highContrast: false,
  fontSize: 'medium' as const,
  showAdvancedFeatures: false,
  enableKeyboardShortcuts: true,
  showDebugInfo: false,
  hasCompletedOnboarding: false,
  hasSeenWelcome: false,
  dismissedTips: [] as string[],
};

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_PREFERENCES,

      setUserMode: (mode) => set({ userMode: mode }),
      
      setTheme: (theme) => set({ theme }),
      
      setChatDensity: (density) => set({ chatDensity: density }),
      
      setShowSuggestions: (show) => set({ showSuggestions: show }),
      
      setSuggestionStyle: (style) => set({ suggestionStyle: style }),
      
      setShowAdvancedFeatures: (show) => set({ showAdvancedFeatures: show }),
      
      setReduceMotion: (reduce) => set({ reduceMotion: reduce }),
      
      setHighContrast: (high) => set({ highContrast: high }),
      
      setFontSize: (size) => set({ fontSize: size }),
      
      completeOnboarding: () => set({ hasCompletedOnboarding: true }),
      
      markWelcomeSeen: () => set({ hasSeenWelcome: true }),
      
      dismissTip: (tipId) =>
        set((state) => ({
          dismissedTips: [...state.dismissedTips, tipId],
        })),
      
      resetPreferences: () => set(DEFAULT_PREFERENCES),

      getEffectiveMode: () => {
        const { userMode, detectedMode } = get();
        if (userMode === 'auto') {
          return detectedMode;
        }
        return userMode;
      },

      shouldShowFeature: (featureLevel) => {
        const { showAdvancedFeatures } = get();
        const effectiveMode = get().getEffectiveMode();

        if (featureLevel === 'basic') return true;
        if (featureLevel === 'intermediate') return effectiveMode === 'technical';
        if (featureLevel === 'advanced') return showAdvancedFeatures && effectiveMode === 'technical';
        return true;
      },
    }),
    {
      name: 'nexusai-preferences',
      partialize: (state) => ({
        userMode: state.userMode,
        theme: state.theme,
        chatDensity: state.chatDensity,
        showTypingIndicator: state.showTypingIndicator,
        showSuggestions: state.showSuggestions,
        suggestionStyle: state.suggestionStyle,
        enableSoundEffects: state.enableSoundEffects,
        enableAnimations: state.enableAnimations,
        showCodeLineNumbers: state.showCodeLineNumbers,
        autoScroll: state.autoScroll,
        reduceMotion: state.reduceMotion,
        highContrast: state.highContrast,
        fontSize: state.fontSize,
        showAdvancedFeatures: state.showAdvancedFeatures,
        enableKeyboardShortcuts: state.enableKeyboardShortcuts,
        hasCompletedOnboarding: state.hasCompletedOnboarding,
        hasSeenWelcome: state.hasSeenWelcome,
        dismissedTips: state.dismissedTips,
      }),
    }
  )
);

/**
 * Hook to check if a feature should be visible based on user mode
 */
export function useFeatureVisibility(level: 'basic' | 'intermediate' | 'advanced'): boolean {
  return usePreferencesStore((state) => state.shouldShowFeature(level));
}

/**
 * Hook to get the effective user mode
 */
export function useUserMode(): 'technical' | 'non-technical' {
  return usePreferencesStore((state) => state.getEffectiveMode());
}

/**
 * Hook for suggestion preferences
 */
export function useSuggestionPreferences() {
  return usePreferencesStore((state) => ({
    show: state.showSuggestions,
    style: state.suggestionStyle,
  }));
}

/**
 * Hook for accessibility preferences
 */
export function useAccessibilityPreferences() {
  return usePreferencesStore((state) => ({
    reduceMotion: state.reduceMotion,
    highContrast: state.highContrast,
    fontSize: state.fontSize,
  }));
}
