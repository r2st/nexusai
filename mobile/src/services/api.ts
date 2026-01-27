/**
 * API Service
 * 
 * Handles all communication with the NexusAI backend.
 */

import axios, { AxiosInstance } from 'axios';
import Constants from 'expo-constants';

const API_BASE_URL = Constants.expoConfig?.extra?.apiUrl || 'https://api.nexusai.dev';

class ApiService {
  private client: AxiosInstance;
  private authToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 60000,
      headers: {
        'Content-Type': 'application/json',
        'X-Client': 'mobile-app',
        'X-Client-Version': '1.0.0',
      },
    });

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      if (this.authToken) {
        config.headers.Authorization = `Bearer ${this.authToken}`;
      }
      return config;
    });
  }

  setAuthToken(token: string | null) {
    this.authToken = token;
  }

  // ==========================================================================
  // Authentication
  // ==========================================================================

  async signIn(email: string, password: string) {
    const response = await this.client.post('/api/v1/auth/login', { email, password });
    return response.data;
  }

  async signUp(email: string, password: string, name: string) {
    const response = await this.client.post('/api/v1/auth/register', { email, password, name });
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get('/api/v1/auth/me');
    return response.data;
  }

  // ==========================================================================
  // Chat
  // ==========================================================================

  async sendMessage(
    message: string,
    conversationId?: string,
    context?: { code?: string; language?: string }
  ) {
    const response = await this.client.post('/api/v1/chat', {
      message,
      conversationId,
      context,
    });
    return response.data;
  }

  async *streamMessage(
    message: string,
    conversationId?: string,
    context?: { code?: string; language?: string }
  ): AsyncGenerator<string, void, unknown> {
    const response = await this.client.post(
      '/api/v1/chat/stream',
      { message, conversationId, context },
      { responseType: 'stream' }
    );

    for await (const chunk of response.data) {
      const text = chunk.toString();
      const lines = text.split('\n').filter((line: string) => line.startsWith('data: '));
      
      for (const line of lines) {
        const data = line.slice(6);
        if (data === '[DONE]') break;
        try {
          const parsed = JSON.parse(data);
          if (parsed.content) {
            yield parsed.content;
          }
        } catch {
          // Skip invalid JSON
        }
      }
    }
  }

  // ==========================================================================
  // Conversations
  // ==========================================================================

  async getConversations(page = 1, limit = 20) {
    const response = await this.client.get('/api/v1/conversations', {
      params: { page, limit },
    });
    return response.data;
  }

  async getConversation(id: string) {
    const response = await this.client.get(`/api/v1/conversations/${id}`);
    return response.data;
  }

  async deleteConversation(id: string) {
    await this.client.delete(`/api/v1/conversations/${id}`);
  }

  async renameConversation(id: string, title: string) {
    const response = await this.client.patch(`/api/v1/conversations/${id}`, { title });
    return response.data;
  }

  // ==========================================================================
  // Analysis
  // ==========================================================================

  async analyzeCode(code: string, language: string) {
    const response = await this.client.post('/api/v1/analyze', { code, language });
    return response.data;
  }

  async explainCode(code: string, language: string, question?: string) {
    const response = await this.client.post('/api/v1/explain', { code, language, question });
    return response.data;
  }

  async generateDocumentation(code: string, language: string) {
    const response = await this.client.post('/api/v1/document', { code, language });
    return response.data;
  }

  // ==========================================================================
  // Projects
  // ==========================================================================

  async getProjects() {
    const response = await this.client.get('/api/v1/projects');
    return response.data;
  }

  async getProjectAnalysis(projectId: string) {
    const response = await this.client.get(`/api/v1/projects/${projectId}/analysis`);
    return response.data;
  }

  async getProjectMetrics(projectId: string) {
    const response = await this.client.get(`/api/v1/projects/${projectId}/metrics`);
    return response.data;
  }
}

export const api = new ApiService();
