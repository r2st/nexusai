import type { WidgetPayload } from './types';

const WIDGET_FENCE_REGEX = /```widget\s*([\s\S]*?)```/g;

// Valid widget types - must match the WidgetPayload union
const VALID_WIDGET_TYPES = ['dora', 'space', 'insights', 'pipeline_progress'] as const;

function isValidWidgetType(type: unknown): type is WidgetPayload['type'] {
  return typeof type === 'string' && VALID_WIDGET_TYPES.includes(type as WidgetPayload['type']);
}

export function parseWidgetBlocks(content: string): {
  content: string;
  widgets: WidgetPayload[];
} {
  const widgets: WidgetPayload[] = [];

  const cleaned = content.replace(WIDGET_FENCE_REGEX, (_match, jsonBlock: string) => {
    const trimmed = jsonBlock.trim();
    if (!trimmed) return '';

    try {
      const parsed = JSON.parse(trimmed);
      if (parsed && typeof parsed === 'object' && 'type' in parsed) {
        // Only add widgets with valid types
        if (isValidWidgetType(parsed.type)) {
          widgets.push(parsed as WidgetPayload);
        } else {
          console.warn('[parseWidgetBlocks] Unknown widget type:', parsed.type, 'Skipping widget.');
        }
      }
    } catch (e) {
      // Log parsing errors for debugging
      console.warn('[parseWidgetBlocks] Failed to parse widget JSON:', e);
    }

    return '';
  });

  return {
    content: cleaned.trim(),
    widgets,
  };
}
