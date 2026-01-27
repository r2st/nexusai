/**
 * Analysis Screen
 * 
 * Shows project analysis, metrics, and code health.
 */

import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../services/api';

interface Project {
  id: string;
  name: string;
  language: string;
  lastAnalysis: string;
  metrics: {
    codeHealth: number;
    complexity: number;
    coverage: number;
    issues: number;
  };
}

export function AnalysisScreen() {
  const { colors } = useTheme();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.getProjects(),
  });

  const projects: Project[] = data?.projects || [];

  const getHealthColor = (score: number) => {
    if (score >= 80) return colors.success;
    if (score >= 60) return colors.warning;
    return colors.error;
  };

  const renderMetricCard = (
    icon: keyof typeof Ionicons.glyphMap,
    label: string,
    value: string | number,
    color?: string
  ) => (
    <View style={[styles.metricCard, { backgroundColor: colors.surface }]}>
      <Ionicons name={icon} size={24} color={color || colors.primary} />
      <Text style={[styles.metricValue, { color: color || colors.text }]}>
        {value}
      </Text>
      <Text style={[styles.metricLabel, { color: colors.textSecondary }]}>
        {label}
      </Text>
    </View>
  );

  const renderProjectCard = (project: Project) => (
    <TouchableOpacity
      key={project.id}
      style={[styles.projectCard, { backgroundColor: colors.surface }]}
    >
      <View style={styles.projectHeader}>
        <View style={styles.projectInfo}>
          <Text style={[styles.projectName, { color: colors.text }]}>
            {project.name}
          </Text>
          <Text style={[styles.projectLanguage, { color: colors.textSecondary }]}>
            {project.language}
          </Text>
        </View>
        <View
          style={[
            styles.healthBadge,
            { backgroundColor: getHealthColor(project.metrics.codeHealth) + '20' },
          ]}
        >
          <Text
            style={[
              styles.healthText,
              { color: getHealthColor(project.metrics.codeHealth) },
            ]}
          >
            {project.metrics.codeHealth}%
          </Text>
        </View>
      </View>

      <View style={styles.projectMetrics}>
        <View style={styles.projectMetric}>
          <Ionicons name="git-branch-outline" size={16} color={colors.textSecondary} />
          <Text style={[styles.projectMetricText, { color: colors.textSecondary }]}>
            Complexity: {project.metrics.complexity}
          </Text>
        </View>
        <View style={styles.projectMetric}>
          <Ionicons name="shield-checkmark-outline" size={16} color={colors.textSecondary} />
          <Text style={[styles.projectMetricText, { color: colors.textSecondary }]}>
            Coverage: {project.metrics.coverage}%
          </Text>
        </View>
        <View style={styles.projectMetric}>
          <Ionicons name="warning-outline" size={16} color={colors.textSecondary} />
          <Text style={[styles.projectMetricText, { color: colors.textSecondary }]}>
            Issues: {project.metrics.issues}
          </Text>
        </View>
      </View>

      <Text style={[styles.lastAnalysis, { color: colors.textTertiary }]}>
        Last analyzed: {new Date(project.lastAnalysis).toLocaleDateString()}
      </Text>
    </TouchableOpacity>
  );

  const renderEmptyState = () => (
    <View style={styles.emptyState}>
      <Ionicons name="analytics-outline" size={64} color={colors.textTertiary} />
      <Text style={[styles.emptyTitle, { color: colors.text }]}>
        No projects yet
      </Text>
      <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
        Connect your repositories to see analysis here
      </Text>
      <TouchableOpacity
        style={[styles.connectButton, { backgroundColor: colors.primary }]}
      >
        <Ionicons name="add" size={20} color="#fff" />
        <Text style={styles.connectButtonText}>Connect Repository</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={isLoading}
          onRefresh={refetch}
          tintColor={colors.primary}
        />
      }
    >
      {/* Overview Metrics */}
      <Text style={[styles.sectionTitle, { color: colors.text }]}>
        Overview
      </Text>
      <View style={styles.metricsGrid}>
        {renderMetricCard('checkmark-circle', 'Code Health', '78%', colors.success)}
        {renderMetricCard('git-branch', 'Repositories', '12')}
        {renderMetricCard('warning', 'Open Issues', '47', colors.warning)}
        {renderMetricCard('shield-checkmark', 'Test Coverage', '64%')}
      </View>

      {/* Projects */}
      <Text style={[styles.sectionTitle, { color: colors.text }]}>
        Projects
      </Text>
      {projects.length > 0 ? (
        projects.map(renderProjectCard)
      ) : (
        renderEmptyState()
      )}
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
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 16,
    marginTop: 8,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 24,
  },
  metricCard: {
    width: '47%',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    gap: 8,
  },
  metricValue: {
    fontSize: 24,
    fontWeight: '700',
  },
  metricLabel: {
    fontSize: 12,
  },
  projectCard: {
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  projectHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  projectInfo: {
    flex: 1,
  },
  projectName: {
    fontSize: 18,
    fontWeight: '600',
  },
  projectLanguage: {
    fontSize: 14,
    marginTop: 2,
  },
  healthBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  healthText: {
    fontSize: 14,
    fontWeight: '600',
  },
  projectMetrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
    marginBottom: 12,
  },
  projectMetric: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  projectMetricText: {
    fontSize: 13,
  },
  lastAnalysis: {
    fontSize: 12,
  },
  emptyState: {
    alignItems: 'center',
    padding: 32,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 16,
  },
  emptySubtitle: {
    fontSize: 14,
    textAlign: 'center',
    marginTop: 8,
    marginBottom: 24,
  },
  connectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
    gap: 8,
  },
  connectButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
