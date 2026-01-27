/**
 * Chat components exports
 * 
 * Conversational AI-focused UI components for the NexusAI chat interface.
 */

// Core chat components
export { ChatMessage } from './message';
export { ChatInput } from './input';
export { ChatSidebar } from './sidebar';

// Enhanced message components
export { TypingIndicator, MessageSkeleton } from './typing-indicator';
export { MessageActions } from './message-actions';
export { CodeBlock, InlineCode } from './code-block';
export { EnhancedMessage } from './enhanced-message';

// Suggestions and guidance
export { SmartSuggestions, COMMON_SUGGESTIONS } from './smart-suggestions';
export { WelcomeMessage } from './welcome-message';

// Context and search
export { ContextPanel } from './context-panel';
export { ConversationSearch } from './conversation-search';
export { QuickActions } from './quick-actions';
export { ModelSelector } from './model-selector';

// Accessibility
export { VoiceInput, VoiceInputButton } from './voice-input';

// Mobile
export { MobileChat } from './mobile-chat';

// Rich content
export {
  ImageMessage,
  ImageGallery,
  DataTable,
  SimpleChart,
  LinkPreview,
} from './rich-content';

// Sharing
export { ShareConversation } from './share-conversation';

// Comments/Threads
export { Comments } from './comments';
