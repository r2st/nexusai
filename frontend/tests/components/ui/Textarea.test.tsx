/**
 * Textarea Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Textarea } from '@/components/ui/textarea';

describe('Textarea', () => {
  it('renders textarea element', () => {
    render(<Textarea data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toBeInTheDocument();
    expect(screen.getByTestId('textarea').tagName).toBe('TEXTAREA');
  });

  it('has correct base styles', () => {
    render(<Textarea data-testid="textarea" />);
    const textarea = screen.getByTestId('textarea');
    expect(textarea).toHaveClass(
      'flex',
      'min-h-[80px]',
      'w-full',
      'rounded-md',
      'border',
      'border-input',
      'bg-background',
      'px-3',
      'py-2',
      'text-sm'
    );
  });

  it('applies custom className', () => {
    render(<Textarea className="min-h-[200px]" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('min-h-[200px]');
  });

  it('forwards ref correctly', () => {
    const ref = { current: null };
    render(<Textarea ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
  });

  it('handles value changes', () => {
    const onChange = vi.fn();
    render(<Textarea onChange={onChange} data-testid="textarea" />);
    
    fireEvent.change(screen.getByTestId('textarea'), {
      target: { value: 'New content' }
    });
    
    expect(onChange).toHaveBeenCalled();
  });

  it('renders with placeholder', () => {
    render(<Textarea placeholder="Enter text here..." data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('placeholder', 'Enter text here...');
  });

  it('renders with default value', () => {
    render(<Textarea defaultValue="Default text" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveValue('Default text');
  });

  it('renders controlled value', () => {
    render(<Textarea value="Controlled text" onChange={() => {}} data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveValue('Controlled text');
  });

  it('renders disabled state', () => {
    render(<Textarea disabled data-testid="textarea" />);
    const textarea = screen.getByTestId('textarea');
    expect(textarea).toBeDisabled();
    expect(textarea).toHaveClass('disabled:cursor-not-allowed', 'disabled:opacity-50');
  });

  it('renders with rows attribute', () => {
    render(<Textarea rows={10} data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('rows', '10');
  });

  it('renders with maxLength', () => {
    render(<Textarea maxLength={500} data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('maxLength', '500');
  });

  it('renders read-only state', () => {
    render(<Textarea readOnly value="Read only text" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('readonly');
  });

  it('renders required attribute', () => {
    render(<Textarea required data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toBeRequired();
  });
});

describe('Textarea Interactions', () => {
  it('handles paste events', () => {
    const onPaste = vi.fn();
    render(<Textarea onPaste={onPaste} data-testid="textarea" />);
    
    fireEvent.paste(screen.getByTestId('textarea'), {
      clipboardData: { getData: () => 'Pasted text' }
    });
    
    expect(onPaste).toHaveBeenCalled();
  });

  it('handles key events', () => {
    const onKeyDown = vi.fn();
    render(<Textarea onKeyDown={onKeyDown} data-testid="textarea" />);
    
    fireEvent.keyDown(screen.getByTestId('textarea'), { key: 'Enter' });
    expect(onKeyDown).toHaveBeenCalled();
  });

  it('can be focused programmatically', () => {
    const ref = { current: null as HTMLTextAreaElement | null };
    render(<Textarea ref={ref} data-testid="textarea" />);
    
    ref.current?.focus();
    expect(document.activeElement).toBe(ref.current);
  });
});

describe('Textarea Accessibility', () => {
  it('supports aria-label', () => {
    render(<Textarea aria-label="Message input" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('aria-label', 'Message input');
  });

  it('supports aria-describedby', () => {
    render(
      <>
        <Textarea aria-describedby="help-text" data-testid="textarea" />
        <span id="help-text">Enter your message</span>
      </>
    );
    expect(screen.getByTestId('textarea')).toHaveAttribute('aria-describedby', 'help-text');
  });

  it('supports aria-invalid', () => {
    render(<Textarea aria-invalid="true" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('aria-invalid', 'true');
  });
});

describe('Textarea Use Cases', () => {
  it('renders message composer', () => {
    render(
      <div>
        <label htmlFor="message">Message</label>
        <Textarea
          id="message"
          placeholder="Type your message..."
          className="resize-none"
          rows={4}
          data-testid="message"
        />
      </div>
    );

    expect(screen.getByLabelText('Message')).toBeInTheDocument();
    expect(screen.getByTestId('message')).toHaveClass('resize-none');
  });

  it('renders with character count', () => {
    const maxLength = 280;
    const value = 'Hello world';
    
    render(
      <div>
        <Textarea value={value} maxLength={maxLength} onChange={() => {}} data-testid="textarea" />
        <span>{value.length}/{maxLength}</span>
      </div>
    );

    expect(screen.getByText('11/280')).toBeInTheDocument();
  });

  it('renders code input', () => {
    render(
      <Textarea
        className="font-mono text-xs"
        placeholder="// Enter code here"
        spellCheck={false}
        data-testid="code-input"
      />
    );

    const textarea = screen.getByTestId('code-input');
    expect(textarea).toHaveClass('font-mono');
    expect(textarea).toHaveAttribute('spellcheck', 'false');
  });
});
