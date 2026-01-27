/**
 * Message Bubble Component
 * 
 * Renders a single chat message with formatting.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';
import Markdown from 'react-native-markdown-display';
import { useTheme } from '../contexts/ThemeContext';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const { colors, isDark } = useTheme();
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    await Clipboard.setStringAsync(message.content);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  };

  const markdownStyles = {
    body: {
      color: colors.text,
      fontSize: 16,
      lineHeight: 24,
    },
    code_inline: {
      backgroundColor: colors.surfaceVariant,
      color: colors.primary,
      paddingHorizontal: 6,
      paddingVertical: 2,
      borderRadius: 4,
      fontSize: 14,
      fontFamily: 'monospace',
    },
    code_block: {
      backgroundColor: isDark ? '#1e1e1e' : '#f5f5f5',
      padding: 12,
      borderRadius: 8,
      fontSize: 14,
      fontFamily: 'monospace',
    },
    fence: {
      backgroundColor: isDark ? '#1e1e1e' : '#f5f5f5',
      padding: 12,
      borderRadius: 8,
      marginVertical: 8,
    },
    link: {
      color: colors.primary,
    },
    strong: {
      fontWeight: '700' as const,
    },
    heading1: {
      fontSize: 24,
      fontWeight: '700' as const,
      marginVertical: 8,
    },
    heading2: {
      fontSize: 20,
      fontWeight: '700' as const,
      marginVertical: 6,
    },
    heading3: {
      fontSize: 18,
      fontWeight: '600' as const,
      marginVertical: 4,
    },
    bullet_list: {
      marginVertical: 4,
    },
    ordered_list: {
      marginVertical: 4,
    },
    list_item: {
      marginVertical: 2,
    },
  };

  return (
    <View
      style={[
        styles.container,
        isUser ? styles.userContainer : styles.assistantContainer,
      ]}
    >
      {/* Avatar */}
      <View
        style={[
          styles.avatar,
          {
            backgroundColor: isUser ? colors.primary : colors.surfaceVariant,
          },
        ]}
      >
        <Ionicons
          name={isUser ? 'person' : 'sparkles'}
          size={16}
          color={isUser ? '#fff' : colors.primary}
        />
      </View>

      {/* Content */}
      <View
        style={[
          styles.bubble,
          {
            backgroundColor: isUser ? colors.primary : colors.surface,
          },
          isUser ? styles.userBubble : styles.assistantBubble,
        ]}
      >
        {isUser ? (
          <Text style={[styles.userText, { color: '#fff' }]}>
            {message.content}
          </Text>
        ) : (
          <Markdown style={markdownStyles}>{message.content}</Markdown>
        )}

        {/* Actions */}
        {!isUser && (
          <View style={styles.actions}>
            <TouchableOpacity style={styles.actionButton} onPress={handleCopy}>
              <Ionicons name="copy-outline" size={16} color={colors.textTertiary} />
            </TouchableOpacity>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginVertical: 8,
    gap: 8,
  },
  userContainer: {
    flexDirection: 'row-reverse',
  },
  assistantContainer: {
    flexDirection: 'row',
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bubble: {
    flex: 1,
    maxWidth: '80%',
    padding: 12,
    borderRadius: 16,
  },
  userBubble: {
    borderTopRightRadius: 4,
  },
  assistantBubble: {
    borderTopLeftRadius: 4,
  },
  userText: {
    fontSize: 16,
    lineHeight: 24,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 8,
    gap: 8,
  },
  actionButton: {
    padding: 4,
  },
});
