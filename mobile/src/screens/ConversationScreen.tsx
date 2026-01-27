/**
 * Conversation Screen
 * 
 * View and continue a specific conversation.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import { useTheme } from '../contexts/ThemeContext';
import { RootStackParamList } from '../navigation';

type ConversationRouteProp = RouteProp<RootStackParamList, 'Conversation'>;

export function ConversationScreen() {
  const { colors } = useTheme();
  const route = useRoute<ConversationRouteProp>();
  const { conversationId } = route.params;

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.text, { color: colors.text }]}>
        Conversation: {conversationId}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  text: {
    fontSize: 16,
  },
});
