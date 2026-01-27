/**
 * Quick Actions Component
 * 
 * Displays quick action buttons for common queries.
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../contexts/ThemeContext';

interface QuickAction {
  id: string;
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  query: string;
}

const quickActions: QuickAction[] = [
  {
    id: '1',
    icon: 'bulb',
    label: 'Explain Code',
    query: 'Explain this code',
  },
  {
    id: '2',
    icon: 'bug',
    label: 'Find Bugs',
    query: 'Find bugs in this code',
  },
  {
    id: '3',
    icon: 'document-text',
    label: 'Generate Docs',
    query: 'Generate documentation for this code',
  },
  {
    id: '4',
    icon: 'flask',
    label: 'Generate Tests',
    query: 'Generate unit tests for this code',
  },
  {
    id: '5',
    icon: 'color-wand',
    label: 'Refactor',
    query: 'How can I improve this code?',
  },
  {
    id: '6',
    icon: 'shield',
    label: 'Security Check',
    query: 'Check this code for security issues',
  },
];

interface QuickActionsProps {
  onAction: (query: string) => void;
}

export function QuickActions({ onAction }: QuickActionsProps) {
  const { colors } = useTheme();

  const handlePress = (action: QuickAction) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onAction(action.query);
  };

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
    >
      {quickActions.map((action) => (
        <TouchableOpacity
          key={action.id}
          style={[styles.actionButton, { backgroundColor: colors.surface }]}
          onPress={() => handlePress(action)}
        >
          <Ionicons name={action.icon} size={20} color={colors.primary} />
          <Text style={[styles.actionLabel, { color: colors.text }]}>
            {action.label}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
    gap: 8,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    gap: 8,
  },
  actionLabel: {
    fontSize: 14,
    fontWeight: '500',
  },
});
