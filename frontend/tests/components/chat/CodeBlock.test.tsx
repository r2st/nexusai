/**
 * CodeBlock Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock CodeBlock component
interface CodeBlockProps {
  code: string;
  language?: string;
  showLineNumbers?: boolean;
  onCopy?: () => void;
}

const CodeBlock = ({
  code,
  language = 'plaintext',
  showLineNumbers = true,
  onCopy,
}: CodeBlockProps) => {
  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    onCopy?.();
  };

  return (
    <div data-testid="code-block" className="code-block">
      <div className="code-header">
        <span data-testid="language-label">{language}</span>
        <button onClick={handleCopy} data-testid="copy-button">Copy</button>
      </div>
      <pre data-testid="code-content" className={showLineNumbers ? 'with-lines' : ''}>
        <code>{code}</code>
      </pre>
    </div>
  );
};

// Mock clipboard API
beforeAll(() => {
  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn().mockResolvedValue(undefined),
    },
  });
});

describe('CodeBlock', () => {
  it('renders code content', () => {
    const code = 'console.log("Hello, World!");';
    render(<CodeBlock code={code} />);
    
    expect(screen.getByTestId('code-content')).toHaveTextContent(code);
  });

  it('displays language label', () => {
    render(<CodeBlock code="const x = 1;" language="javascript" />);
    expect(screen.getByTestId('language-label')).toHaveTextContent('javascript');
  });

  it('defaults to plaintext language', () => {
    render(<CodeBlock code="some text" />);
    expect(screen.getByTestId('language-label')).toHaveTextContent('plaintext');
  });

  it('renders copy button', () => {
    render(<CodeBlock code="test" />);
    expect(screen.getByTestId('copy-button')).toBeInTheDocument();
  });

  it('copies code to clipboard when copy button is clicked', async () => {
    const code = 'const x = 42;';
    const onCopy = vi.fn();
    render(<CodeBlock code={code} onCopy={onCopy} />);
    
    fireEvent.click(screen.getByTestId('copy-button'));
    
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(code);
  });

  it('calls onCopy callback', async () => {
    const onCopy = vi.fn();
    render(<CodeBlock code="test" onCopy={onCopy} />);
    
    fireEvent.click(screen.getByTestId('copy-button'));
    
    await vi.waitFor(() => {
      expect(onCopy).toHaveBeenCalled();
    });
  });

  it('shows line numbers by default', () => {
    render(<CodeBlock code="line1\nline2" />);
    expect(screen.getByTestId('code-content')).toHaveClass('with-lines');
  });

  it('hides line numbers when disabled', () => {
    render(<CodeBlock code="line1\nline2" showLineNumbers={false} />);
    expect(screen.getByTestId('code-content')).not.toHaveClass('with-lines');
  });
});

describe('CodeBlock Languages', () => {
  const languages = ['javascript', 'typescript', 'python', 'rust', 'go', 'java'];
  
  languages.forEach((lang) => {
    it(`renders ${lang} code block`, () => {
      render(<CodeBlock code={`// ${lang} code`} language={lang} />);
      expect(screen.getByTestId('language-label')).toHaveTextContent(lang);
    });
  });
});

describe('CodeBlock Multi-line', () => {
  it('renders multi-line code', () => {
    const multiLineCode = `function hello() {
  console.log("Hello");
  return true;
}`;
    render(<CodeBlock code={multiLineCode} language="javascript" />);
    
    expect(screen.getByTestId('code-content')).toHaveTextContent('function hello()');
    expect(screen.getByTestId('code-content')).toHaveTextContent('console.log');
    expect(screen.getByTestId('code-content')).toHaveTextContent('return true');
  });

  it('preserves whitespace and indentation', () => {
    const code = '  indented\n    more indented';
    render(<CodeBlock code={code} />);
    
    const content = screen.getByTestId('code-content');
    expect(content.textContent).toContain('  indented');
    expect(content.textContent).toContain('    more indented');
  });
});

describe('CodeBlock Edge Cases', () => {
  it('handles empty code', () => {
    render(<CodeBlock code="" />);
    expect(screen.getByTestId('code-content')).toBeInTheDocument();
  });

  it('handles special characters', () => {
    const code = '<div class="test">&nbsp;</div>';
    render(<CodeBlock code={code} language="html" />);
    expect(screen.getByTestId('code-content')).toHaveTextContent(code);
  });

  it('handles very long lines', () => {
    const longLine = 'a'.repeat(1000);
    render(<CodeBlock code={longLine} />);
    expect(screen.getByTestId('code-content')).toHaveTextContent(longLine);
  });
});
