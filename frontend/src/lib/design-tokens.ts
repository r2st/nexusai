/**
 * Design System Tokens
 * 
 * Centralized design tokens for consistent styling across the application.
 * Based on the conversational AI UI/UX principles and accessibility requirements.
 */

// =============================================================================
// Color Tokens
// =============================================================================

export const colors = {
  // Primary brand colors
  primary: {
    50: 'hsl(221 83% 97%)',
    100: 'hsl(221 83% 93%)',
    200: 'hsl(221 83% 87%)',
    300: 'hsl(221 83% 77%)',
    400: 'hsl(221 83% 65%)',
    500: 'hsl(221 83% 53%)', // Main primary
    600: 'hsl(221 83% 45%)',
    700: 'hsl(221 83% 38%)',
    800: 'hsl(221 83% 31%)',
    900: 'hsl(221 83% 25%)',
    950: 'hsl(221 83% 17%)',
  },

  // Semantic colors
  success: {
    light: 'hsl(142 76% 36%)',
    DEFAULT: 'hsl(142 71% 45%)',
    dark: 'hsl(142 76% 30%)',
  },
  warning: {
    light: 'hsl(38 92% 50%)',
    DEFAULT: 'hsl(38 92% 45%)',
    dark: 'hsl(38 92% 35%)',
  },
  error: {
    light: 'hsl(0 84% 60%)',
    DEFAULT: 'hsl(0 84% 50%)',
    dark: 'hsl(0 84% 40%)',
  },
  info: {
    light: 'hsl(199 89% 48%)',
    DEFAULT: 'hsl(199 89% 40%)',
    dark: 'hsl(199 89% 32%)',
  },

  // Chat-specific colors
  chat: {
    userBubble: 'hsl(var(--primary))',
    userBubbleForeground: 'hsl(var(--primary-foreground))',
    assistantBubble: 'hsl(var(--muted))',
    assistantBubbleForeground: 'hsl(var(--foreground))',
    systemBubble: 'hsl(var(--secondary))',
    systemBubbleForeground: 'hsl(var(--secondary-foreground))',
  },
};

// =============================================================================
// Typography Tokens
// =============================================================================

export const typography = {
  // Font families
  fontFamily: {
    sans: 'var(--font-sans, ui-sans-serif, system-ui, -apple-system, sans-serif)',
    mono: 'var(--font-mono, ui-monospace, SFMono-Regular, Menlo, Monaco, monospace)',
  },

  // Font sizes (using rem for accessibility)
  fontSize: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
  },

  // Line heights
  lineHeight: {
    none: '1',
    tight: '1.25',
    snug: '1.375',
    normal: '1.5',
    relaxed: '1.625',
    loose: '2',
  },

  // Font weights
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
};

// =============================================================================
// Spacing Tokens (8px grid system)
// =============================================================================

export const spacing = {
  0: '0px',
  0.5: '0.125rem',  // 2px
  1: '0.25rem',     // 4px
  1.5: '0.375rem',  // 6px
  2: '0.5rem',      // 8px
  2.5: '0.625rem',  // 10px
  3: '0.75rem',     // 12px
  3.5: '0.875rem',  // 14px
  4: '1rem',        // 16px
  5: '1.25rem',     // 20px
  6: '1.5rem',      // 24px
  7: '1.75rem',     // 28px
  8: '2rem',        // 32px
  9: '2.25rem',     // 36px
  10: '2.5rem',     // 40px
  11: '2.75rem',    // 44px
  12: '3rem',       // 48px
  14: '3.5rem',     // 56px
  16: '4rem',       // 64px
  20: '5rem',       // 80px
  24: '6rem',       // 96px
};

// =============================================================================
// Animation Tokens
// =============================================================================

export const animation = {
  // Durations
  duration: {
    fastest: '50ms',
    fast: '100ms',
    normal: '200ms',
    slow: '300ms',
    slower: '400ms',
    slowest: '500ms',
  },

  // Easing curves
  easing: {
    linear: 'linear',
    ease: 'ease',
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },

  // Common animations
  keyframes: {
    fadeIn: {
      from: { opacity: '0' },
      to: { opacity: '1' },
    },
    fadeOut: {
      from: { opacity: '1' },
      to: { opacity: '0' },
    },
    slideUp: {
      from: { transform: 'translateY(10px)', opacity: '0' },
      to: { transform: 'translateY(0)', opacity: '1' },
    },
    slideDown: {
      from: { transform: 'translateY(-10px)', opacity: '0' },
      to: { transform: 'translateY(0)', opacity: '1' },
    },
    pulse: {
      '0%, 100%': { opacity: '1' },
      '50%': { opacity: '0.5' },
    },
    bounce: {
      '0%, 100%': { transform: 'translateY(0)' },
      '50%': { transform: 'translateY(-25%)' },
    },
    typing: {
      '0%, 100%': { opacity: '0.3' },
      '50%': { opacity: '1' },
    },
  },
};

// =============================================================================
// Shadow Tokens (Elevation)
// =============================================================================

export const shadows = {
  none: 'none',
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
  inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
};

// =============================================================================
// Border Radius Tokens
// =============================================================================

export const borderRadius = {
  none: '0px',
  sm: '0.125rem',   // 2px
  DEFAULT: '0.25rem', // 4px
  md: '0.375rem',   // 6px
  lg: '0.5rem',     // 8px
  xl: '0.75rem',    // 12px
  '2xl': '1rem',    // 16px
  '3xl': '1.5rem',  // 24px
  full: '9999px',
};

// =============================================================================
// Z-Index Tokens
// =============================================================================

export const zIndex = {
  auto: 'auto',
  0: '0',
  10: '10',
  20: '20',
  30: '30',
  40: '40',
  50: '50', // Modals, dialogs
  60: '60', // Toasts
  70: '70', // Tooltips
  80: '80', // Dropdowns
  90: '90', // Command palette
  100: '100', // Maximum
};

// =============================================================================
// Breakpoints
// =============================================================================

export const breakpoints = {
  xs: '320px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

// =============================================================================
// Chat-Specific Tokens
// =============================================================================

export const chatTokens = {
  // Message spacing based on density
  messagePadding: {
    compact: spacing[3],
    comfortable: spacing[4],
    spacious: spacing[6],
  },
  
  messageGap: {
    compact: spacing[2],
    comfortable: spacing[4],
    spacious: spacing[6],
  },

  // Avatar sizes
  avatarSize: {
    sm: '24px',
    md: '32px',
    lg: '40px',
  },

  // Input area
  inputMaxHeight: '200px',
  inputMinHeight: '40px',

  // Sidebar
  sidebarWidth: '280px',
  sidebarCollapsedWidth: '64px',

  // Max content width
  maxContentWidth: '768px',
};

// =============================================================================
// Exports
// =============================================================================

export const designTokens = {
  colors,
  typography,
  spacing,
  animation,
  shadows,
  borderRadius,
  zIndex,
  breakpoints,
  chat: chatTokens,
};

export default designTokens;
