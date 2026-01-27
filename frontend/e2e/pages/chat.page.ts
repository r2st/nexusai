/**
 * Chat Page Object
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class ChatPage extends BasePage {
  readonly url = '/chat';

  // Sidebar Locators
  readonly sidebar: Locator;
  readonly newChatButton: Locator;
  readonly conversationList: Locator;
  readonly conversationItems: Locator;

  // Main Chat Area Locators
  readonly chatContainer: Locator;
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly messageList: Locator;
  readonly userMessages: Locator;
  readonly assistantMessages: Locator;
  readonly welcomeMessage: Locator;
  readonly loadingIndicator: Locator;
  readonly streamingMessage: Locator;

  // Header Locators
  readonly modelSelector: Locator;
  readonly settingsButton: Locator;
  readonly userMenu: Locator;
  readonly logoutButton: Locator;

  constructor(page: Page) {
    super(page);

    // Sidebar
    this.sidebar = page.locator('[data-sidebar], aside').first();
    this.newChatButton = page.locator('[data-testid="new-chat-button"], button:has-text("New Chat")').first();
    this.conversationList = page.locator('[data-conversation-list], .space-y-1').first();
    this.conversationItems = page.locator('[data-conversation-item]');

    // Main Chat Area
    this.chatContainer = page.locator('main[role="main"]').first();
    // Match both the ChatInput component and the ChatComposer component
    this.messageInput = page.locator('textarea[placeholder*="Send a message"], textarea[aria-label="Message input"], [data-chat-input]').first();
    this.sendButton = page.locator('button[aria-label="Send message"], button:has(svg.lucide-send)').first();
    this.messageList = page.locator('[data-message-list]');
    // Match message bubbles by role or content wrapper
    this.userMessages = page.locator('[data-role="user"], .group:has(div:has-text("You"))');
    this.assistantMessages = page.locator('[data-role="assistant"], .group:has(div:has-text("Assistant"))');
    this.welcomeMessage = page.getByText(/how can i help|welcome to nexusai|start the conversation/i);
    // Use more specific locator for loading indicator - the status rail shows "Responding"
    this.loadingIndicator = page.locator('div:has-text("Responding"), .sr-only[aria-busy="true"]').first();
    this.streamingMessage = page.locator('[data-streaming="true"]');

    // Header
    this.modelSelector = page.locator('[data-model-selector]');
    this.settingsButton = page.locator('button[data-nav="settings"], button:has-text("Settings")');
    this.userMenu = page.locator('[data-user-menu]');
    this.logoutButton = page.getByRole('button', { name: /logout|sign out/i });
  }

  /**
   * Send a message
   * Note: If no conversation is active, this will create one and navigate.
   * The message will then be sent from the conversation page.
   */
  async sendMessage(message: string): Promise<void> {
    // Wait for the input to be ready
    await this.messageInput.waitFor({ state: 'visible', timeout: 10000 });

    // Focus and fill the input
    await this.messageInput.click();
    await this.messageInput.fill(message);

    // Wait a bit for the send button to become enabled
    await this.page.waitForTimeout(100);

    // Click send button
    await this.sendButton.waitFor({ state: 'visible', timeout: 5000 });

    // Check the current URL before sending
    const urlBefore = this.page.url();
    const isOnNewChatPage = urlBefore.endsWith('/chat') || urlBefore.endsWith('/chat/');

    await this.sendButton.click();

    // If we were on /chat (no conversation), sending creates a new conversation
    // and navigates to /chat/{id}. We need to wait for navigation and send again.
    if (isOnNewChatPage) {
      // Wait for navigation to a conversation page
      await this.page.waitForURL(/\/chat\/[^/]+$/, { timeout: 15000 });

      // Wait for the page to load
      await this.page.waitForLoadState('domcontentloaded');
      await this.page.waitForTimeout(500);

      // Now send the actual message from the conversation page
      await this.messageInput.waitFor({ state: 'visible', timeout: 10000 });
      await this.messageInput.click();
      await this.messageInput.fill(message);
      await this.page.waitForTimeout(100);
      await this.sendButton.waitFor({ state: 'visible', timeout: 5000 });
      await this.sendButton.click();
    }
  }

  /**
   * Send a message and wait for response
   */
  async sendMessageAndWaitForResponse(message: string, timeout = 60000): Promise<void> {
    const initialCount = await this.assistantMessages.count();

    await this.sendMessage(message);

    // Wait for loading to start
    await expect(this.loadingIndicator).toBeVisible({ timeout: 5000 }).catch(() => {});

    // Wait for a new assistant message
    await expect(this.assistantMessages).toHaveCount(initialCount + 1, { timeout });

    // Wait for streaming to complete
    await expect(this.streamingMessage).toBeHidden({ timeout }).catch(() => {});
  }

  /**
   * Send message using Enter key
   */
  async sendMessageWithEnter(message: string): Promise<void> {
    await this.messageInput.fill(message);
    await this.messageInput.press('Enter');
  }

  /**
   * Start a new conversation
   */
  async startNewChat(): Promise<void> {
    await this.newChatButton.click();
    await this.page.waitForURL(/\/chat(\/[^/]+)?$/);
  }

  /**
   * Select a conversation from the sidebar
   */
  async selectConversation(index: number): Promise<void> {
    const conversation = this.conversationItems.nth(index);
    await conversation.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Select conversation by title
   */
  async selectConversationByTitle(title: string | RegExp): Promise<void> {
    const conversation = this.conversationItems.filter({ hasText: title });
    await conversation.click();
    await this.waitForLoadingComplete();
  }

  /**
   * Delete a conversation
   */
  async deleteConversation(index: number): Promise<void> {
    const conversation = this.conversationItems.nth(index);
    await conversation.hover();

    const deleteButton = conversation.locator('button[aria-label="Delete conversation"], [data-testid="delete-conversation"]');
    await deleteButton.click();

    // Confirm deletion if dialog appears
    const confirmButton = this.page.getByRole('button', { name: /confirm|yes|delete/i });
    if (await confirmButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmButton.click();
    }
  }

  /**
   * Get message count
   */
  async getMessageCount(): Promise<{ user: number; assistant: number; total: number }> {
    const user = await this.userMessages.count();
    const assistant = await this.assistantMessages.count();
    return { user, assistant, total: user + assistant };
  }

  /**
   * Get last message content
   */
  async getLastMessageContent(role: 'user' | 'assistant'): Promise<string> {
    const messages = role === 'user' ? this.userMessages : this.assistantMessages;

    // Wait for at least one message to exist
    await messages.first().waitFor({ state: 'visible', timeout: 30000 });

    return messages.last().textContent() ?? '';
  }

  /**
   * Get all messages
   */
  async getAllMessages(): Promise<Array<{ role: string; content: string }>> {
    const messages: Array<{ role: string; content: string }> = [];

    const allMessages = this.page.locator('[data-role]');
    const count = await allMessages.count();

    for (let i = 0; i < count; i++) {
      const message = allMessages.nth(i);
      const role = await message.getAttribute('data-role') ?? 'unknown';
      const content = await message.textContent() ?? '';
      messages.push({ role, content });
    }

    return messages;
  }

  /**
   * Get conversation count
   */
  async getConversationCount(): Promise<number> {
    return this.conversationItems.count();
  }

  /**
   * Change model
   */
  async selectModel(modelName: string): Promise<void> {
    await this.modelSelector.click();
    const modelOption = this.page.getByRole('option', { name: modelName });
    await modelOption.click();
  }

  /**
   * Open settings
   */
  async openSettings(): Promise<void> {
    await this.settingsButton.click();
  }

  /**
   * Logout
   */
  async logout(): Promise<void> {
    await this.userMenu.click();
    await this.logoutButton.click();
    await this.page.waitForURL(/\/login/);
  }

  /**
   * Assert chat page is loaded
   */
  async assertPageLoaded(): Promise<void> {
    await expect(this.messageInput).toBeVisible();
    await expect(this.sidebar).toBeVisible();
  }

  /**
   * Assert welcome message is displayed
   */
  async assertWelcomeDisplayed(): Promise<void> {
    await expect(this.welcomeMessage).toBeVisible();
  }

  /**
   * Assert message was sent
   */
  async assertMessageSent(content: string | RegExp): Promise<void> {
    const message = this.userMessages.filter({ hasText: content });
    await expect(message).toBeVisible();
  }

  /**
   * Assert response was received
   */
  async assertResponseReceived(): Promise<void> {
    await expect(this.assistantMessages.last()).toBeVisible();
    const content = await this.assistantMessages.last().textContent();
    expect(content?.length).toBeGreaterThan(0);
  }

  /**
   * Assert loading indicator
   */
  async assertLoading(): Promise<void> {
    await expect(this.loadingIndicator).toBeVisible();
  }

  /**
   * Assert not loading
   */
  async assertNotLoading(): Promise<void> {
    await expect(this.loadingIndicator).toBeHidden();
  }

  /**
   * Assert conversation exists
   */
  async assertConversationExists(title: string | RegExp): Promise<void> {
    const conversation = this.conversationItems.filter({ hasText: title });
    await expect(conversation).toBeVisible();
  }

  /**
   * Assert conversation deleted
   */
  async assertConversationDeleted(title: string | RegExp): Promise<void> {
    const conversation = this.conversationItems.filter({ hasText: title });
    await expect(conversation).toBeHidden();
  }

  /**
   * Assert empty state
   */
  async assertEmptyState(): Promise<void> {
    const emptyMessage = this.page.getByText(/no conversations|start a conversation/i);
    await expect(emptyMessage).toBeVisible();
  }

  /**
   * Wait for streaming to complete
   */
  async waitForStreamingComplete(timeout = 60000): Promise<void> {
    // Wait for "Responding" text to disappear (the status rail indicator)
    const respondingIndicator = this.page.locator('text=Responding');
    await expect(respondingIndicator).toBeHidden({ timeout });

    // Also wait for any streaming message indicators to disappear
    const streamingIndicator = this.page.locator('[data-streaming="true"]');
    await expect(streamingIndicator).toBeHidden({ timeout: 5000 }).catch(() => {});
  }

  /**
   * Assert markdown rendering
   */
  async assertMarkdownRendered(): Promise<void> {
    const codeBlock = this.assistantMessages.last().locator('pre code, code');
    const isCodeRendered = await codeBlock.isVisible().catch(() => false);

    if (!isCodeRendered) {
      // Check for other markdown elements
      const markdownElements = this.assistantMessages.last().locator('strong, em, ul, ol, a, h1, h2, h3');
      expect(await markdownElements.count()).toBeGreaterThan(0);
    }
  }
}
