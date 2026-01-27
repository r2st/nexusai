/**
 * Settings Screen
 * 
 * App settings and user preferences.
 */

import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Switch,
  StyleSheet,
  Alert,
  Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import Constants from 'expo-constants';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';

export function SettingsScreen() {
  const { colors, mode, setMode, isDark } = useTheme();
  const { user, signOut } = useAuth();

  const handleSignOut = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Sign Out', style: 'destructive', onPress: signOut },
      ]
    );
  };

  const handleThemeChange = (value: boolean) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setMode(value ? 'dark' : 'light');
  };

  const renderSettingRow = (
    icon: keyof typeof Ionicons.glyphMap,
    label: string,
    value?: string | React.ReactNode,
    onPress?: () => void
  ) => (
    <TouchableOpacity
      style={[styles.settingRow, { backgroundColor: colors.surface }]}
      onPress={onPress}
      disabled={!onPress}
    >
      <View style={styles.settingLeft}>
        <View style={[styles.iconContainer, { backgroundColor: colors.primary + '20' }]}>
          <Ionicons name={icon} size={20} color={colors.primary} />
        </View>
        <Text style={[styles.settingLabel, { color: colors.text }]}>{label}</Text>
      </View>
      {typeof value === 'string' ? (
        <Text style={[styles.settingValue, { color: colors.textSecondary }]}>{value}</Text>
      ) : (
        value
      )}
      {onPress && !value && (
        <Ionicons name="chevron-forward" size={20} color={colors.textTertiary} />
      )}
    </TouchableOpacity>
  );

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.content}
    >
      {/* Account */}
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
        ACCOUNT
      </Text>
      <View style={[styles.section, { backgroundColor: colors.surface }]}>
        <View style={styles.profileRow}>
          <View style={[styles.avatar, { backgroundColor: colors.primary }]}>
            <Text style={styles.avatarText}>
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </Text>
          </View>
          <View style={styles.profileInfo}>
            <Text style={[styles.profileName, { color: colors.text }]}>
              {user?.name || 'User'}
            </Text>
            <Text style={[styles.profileEmail, { color: colors.textSecondary }]}>
              {user?.email || 'user@example.com'}
            </Text>
          </View>
        </View>
      </View>

      {/* Preferences */}
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
        PREFERENCES
      </Text>
      <View style={styles.section}>
        {renderSettingRow(
          'moon',
          'Dark Mode',
          <Switch
            value={isDark}
            onValueChange={handleThemeChange}
            trackColor={{ false: colors.border, true: colors.primary }}
            thumbColor="#fff"
          />
        )}
        {renderSettingRow('notifications', 'Notifications', undefined, () => {
          Linking.openSettings();
        })}
        {renderSettingRow('language', 'Language', 'English')}
      </View>

      {/* AI Settings */}
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
        AI SETTINGS
      </Text>
      <View style={styles.section}>
        {renderSettingRow('hardware-chip', 'Model', 'Auto')}
        {renderSettingRow('speedometer', 'Response Style', 'Balanced')}
        {renderSettingRow('code-slash', 'Code Format', 'Auto-detect')}
      </View>

      {/* Support */}
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
        SUPPORT
      </Text>
      <View style={styles.section}>
        {renderSettingRow('help-circle', 'Help Center', undefined, () => {
          Linking.openURL('https://docs.nexusai.dev');
        })}
        {renderSettingRow('chatbubble', 'Contact Support', undefined, () => {
          Linking.openURL('mailto:support@nexusai.dev');
        })}
        {renderSettingRow('document-text', 'Privacy Policy', undefined, () => {
          Linking.openURL('https://nexusai.dev/privacy');
        })}
        {renderSettingRow('shield', 'Terms of Service', undefined, () => {
          Linking.openURL('https://nexusai.dev/terms');
        })}
      </View>

      {/* About */}
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
        ABOUT
      </Text>
      <View style={styles.section}>
        {renderSettingRow(
          'information-circle',
          'Version',
          Constants.expoConfig?.version || '1.0.0'
        )}
        {renderSettingRow('star', 'Rate the App', undefined, () => {
          // Open app store page
        })}
      </View>

      {/* Sign Out */}
      <TouchableOpacity
        style={[styles.signOutButton, { backgroundColor: colors.surface }]}
        onPress={handleSignOut}
      >
        <Ionicons name="log-out" size={20} color={colors.error} />
        <Text style={[styles.signOutText, { color: colors.error }]}>Sign Out</Text>
      </TouchableOpacity>

      <Text style={[styles.footer, { color: colors.textTertiary }]}>
        Made with ❤️ by NexusAI Team
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 0.5,
    marginTop: 24,
    marginBottom: 8,
    marginLeft: 4,
  },
  section: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconContainer: {
    width: 36,
    height: 36,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  settingLabel: {
    fontSize: 16,
  },
  settingValue: {
    fontSize: 16,
  },
  profileRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    gap: 12,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '700',
  },
  profileInfo: {
    flex: 1,
  },
  profileName: {
    fontSize: 18,
    fontWeight: '600',
  },
  profileEmail: {
    fontSize: 14,
    marginTop: 2,
  },
  signOutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 32,
    padding: 16,
    borderRadius: 12,
  },
  signOutText: {
    fontSize: 16,
    fontWeight: '600',
  },
  footer: {
    textAlign: 'center',
    marginTop: 32,
    fontSize: 14,
  },
});
