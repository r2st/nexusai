'use client';

import { useState, useCallback } from 'react';
import { Check, Copy, Download, Play, Terminal } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
  theme?: 'dark' | 'light' | 'auto';
  maxHeight?: number;
  onRun?: (code: string) => void;
  className?: string;
}

/**
 * Enhanced code block with syntax highlighting, copy, and actions.
 * 
 * Features:
 * - Syntax highlighting for 100+ languages
 * - One-click copy
 * - Optional line numbers
 * - Run button for executable code
 * - Download as file
 */
export function CodeBlock({
  code,
  language = 'text',
  filename,
  showLineNumbers = true,
  theme = 'auto',
  maxHeight = 400,
  onRun,
  className,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  // Detect system theme
  const isDarkMode =
    theme === 'dark' ||
    (theme === 'auto' &&
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast.success('Code copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('Failed to copy code');
    }
  }, [code]);

  const handleDownload = useCallback(() => {
    const extension = getExtensionForLanguage(language);
    const name = filename || `code.${extension}`;
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Downloaded ${name}`);
  }, [code, language, filename]);

  const handleRun = useCallback(() => {
    onRun?.(code);
  }, [code, onRun]);

  const isRunnable = ['javascript', 'js', 'typescript', 'ts', 'python', 'py', 'shell', 'bash'].includes(
    language.toLowerCase()
  );

  return (
    <div
      className={cn(
        'group relative rounded-lg border bg-muted/50 overflow-hidden',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/80">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Terminal className="h-4 w-4" aria-hidden="true" />
          <span className="font-mono">
            {filename || language}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          {isRunnable && onRun && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={handleRun}
              title="Run code"
            >
              <Play className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
              Run
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleDownload}
            title="Download file"
            aria-label="Download code as file"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleCopy}
            title="Copy code"
            aria-label="Copy code to clipboard"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-green-500" aria-hidden="true" />
            ) : (
              <Copy className="h-3.5 w-3.5" aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>

      {/* Code */}
      <div
        className="overflow-auto"
        style={{ maxHeight }}
      >
        <SyntaxHighlighter
          language={normalizeLanguage(language)}
          style={isDarkMode ? oneDark : oneLight}
          showLineNumbers={showLineNumbers}
          customStyle={{
            margin: 0,
            padding: '1rem',
            background: 'transparent',
            fontSize: '0.875rem',
          }}
          codeTagProps={{
            style: {
              fontFamily: 'var(--font-mono, ui-monospace, monospace)',
            },
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

/**
 * Inline code component for short code snippets
 */
export function InlineCode({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <code
      className={cn(
        'px-1.5 py-0.5 rounded bg-muted font-mono text-sm',
        className
      )}
    >
      {children}
    </code>
  );
}

/**
 * Normalize language name for syntax highlighter
 */
function normalizeLanguage(lang: string): string {
  const map: Record<string, string> = {
    js: 'javascript',
    ts: 'typescript',
    py: 'python',
    rb: 'ruby',
    sh: 'bash',
    shell: 'bash',
    yml: 'yaml',
    md: 'markdown',
    dockerfile: 'docker',
  };
  return map[lang.toLowerCase()] || lang.toLowerCase();
}

/**
 * Get file extension for language
 */
function getExtensionForLanguage(lang: string): string {
  const map: Record<string, string> = {
    javascript: 'js',
    typescript: 'ts',
    python: 'py',
    ruby: 'rb',
    bash: 'sh',
    shell: 'sh',
    yaml: 'yml',
    markdown: 'md',
    json: 'json',
    html: 'html',
    css: 'css',
    sql: 'sql',
    go: 'go',
    rust: 'rs',
    java: 'java',
    kotlin: 'kt',
    swift: 'swift',
    csharp: 'cs',
    cpp: 'cpp',
    c: 'c',
  };
  return map[lang.toLowerCase()] || 'txt';
}

export default CodeBlock;
