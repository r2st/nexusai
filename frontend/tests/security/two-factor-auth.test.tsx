/**
 * Tests for Two-Factor Authentication Components
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import {
  OTPInput,
  TwoFactorVerify,
  BackupCodeInput,
} from '@/components/security/two-factor-auth';

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock api
vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: { enabled: false } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

describe('OTPInput', () => {
  it('renders correct number of input fields', () => {
    render(
      <OTPInput value="" onChange={() => {}} />
    );

    const inputs = screen.getAllByRole('textbox');
    expect(inputs).toHaveLength(6);
  });

  it('renders custom number of fields', () => {
    render(
      <OTPInput value="" onChange={() => {}} length={4} />
    );

    const inputs = screen.getAllByRole('textbox');
    expect(inputs).toHaveLength(4);
  });

  it('displays current value across fields', () => {
    render(
      <OTPInput value="123456" onChange={() => {}} />
    );

    const inputs = screen.getAllByRole('textbox');
    expect(inputs[0]).toHaveValue('1');
    expect(inputs[1]).toHaveValue('2');
    expect(inputs[2]).toHaveValue('3');
    expect(inputs[3]).toHaveValue('4');
    expect(inputs[4]).toHaveValue('5');
    expect(inputs[5]).toHaveValue('6');
  });

  it('calls onChange when typing', async () => {
    const handleChange = vi.fn();
    render(
      <OTPInput value="" onChange={handleChange} />
    );

    const inputs = screen.getAllByRole('textbox');
    await act(async () => {
      fireEvent.change(inputs[0], { target: { value: '1' } });
    });

    expect(handleChange).toHaveBeenCalledWith('1');
  });

  it('only accepts digits', async () => {
    const handleChange = vi.fn();
    render(
      <OTPInput value="" onChange={handleChange} />
    );

    const inputs = screen.getAllByRole('textbox');
    await act(async () => {
      fireEvent.change(inputs[0], { target: { value: 'a' } });
    });

    // Should not call onChange with non-digit
    expect(handleChange).not.toHaveBeenCalledWith('a');
  });

  it('handles paste event', async () => {
    const handleChange = vi.fn();
    render(
      <OTPInput value="" onChange={handleChange} />
    );

    const inputs = screen.getAllByRole('textbox');
    
    // Simulate paste
    fireEvent.paste(inputs[0], {
      clipboardData: {
        getData: () => '123456',
      },
    });

    expect(handleChange).toHaveBeenCalledWith('123456');
  });

  it('calls onComplete when all digits entered', async () => {
    const handleComplete = vi.fn();
    let currentValue = '';
    
    const { rerender } = render(
      <OTPInput 
        value={currentValue} 
        onChange={(v) => { currentValue = v; }} 
        onComplete={handleComplete} 
      />
    );

    const inputs = screen.getAllByRole('textbox');
    
    // Simulate paste of full code
    fireEvent.paste(inputs[0], {
      clipboardData: {
        getData: () => '123456',
      },
    });

    expect(handleComplete).toHaveBeenCalled();
  });

  it('can be disabled', () => {
    render(
      <OTPInput value="" onChange={() => {}} disabled />
    );

    const inputs = screen.getAllByRole('textbox');
    inputs.forEach(input => {
      expect(input).toBeDisabled();
    });
  });
});

describe('TwoFactorVerify', () => {
  it('renders verification modal', () => {
    render(
      <TwoFactorVerify
        onVerify={async () => {}}
        onCancel={() => {}}
        onUseBackupCode={() => {}}
      />
    );

    expect(screen.getByText('Two-Factor Authentication')).toBeInTheDocument();
    expect(screen.getByText(/Enter the code from your authenticator/)).toBeInTheDocument();
  });

  it('renders verify button', () => {
    render(
      <TwoFactorVerify
        onVerify={async () => {}}
        onCancel={() => {}}
        onUseBackupCode={() => {}}
      />
    );

    expect(screen.getByRole('button', { name: /verify/i })).toBeInTheDocument();
  });

  it('calls onCancel when cancel button clicked', async () => {
    const handleCancel = vi.fn();
    render(
      <TwoFactorVerify
        onVerify={async () => {}}
        onCancel={handleCancel}
        onUseBackupCode={() => {}}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(handleCancel).toHaveBeenCalled();
  });

  it('calls onUseBackupCode when backup code button clicked', async () => {
    const handleBackupCode = vi.fn();
    render(
      <TwoFactorVerify
        onVerify={async () => {}}
        onCancel={() => {}}
        onUseBackupCode={handleBackupCode}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /use backup code/i }));
    expect(handleBackupCode).toHaveBeenCalled();
  });

  it('disables verify button for incomplete code', () => {
    render(
      <TwoFactorVerify
        onVerify={async () => {}}
        onCancel={() => {}}
        onUseBackupCode={() => {}}
      />
    );

    const verifyButton = screen.getByRole('button', { name: /verify/i });
    expect(verifyButton).toBeDisabled();
  });
});

describe('BackupCodeInput', () => {
  it('renders backup code modal', () => {
    render(
      <BackupCodeInput
        onVerify={async () => {}}
        onCancel={() => {}}
        onBack={() => {}}
      />
    );

    expect(screen.getByText('Use Backup Code')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('XXXX-XXXX')).toBeInTheDocument();
  });

  it('calls onCancel when cancel button clicked', async () => {
    const handleCancel = vi.fn();
    render(
      <BackupCodeInput
        onVerify={async () => {}}
        onCancel={handleCancel}
        onBack={() => {}}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(handleCancel).toHaveBeenCalled();
  });

  it('calls onBack when use authenticator button clicked', async () => {
    const handleBack = vi.fn();
    render(
      <BackupCodeInput
        onVerify={async () => {}}
        onCancel={() => {}}
        onBack={handleBack}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /use authenticator/i }));
    expect(handleBack).toHaveBeenCalled();
  });

  it('converts input to uppercase', async () => {
    render(
      <BackupCodeInput
        onVerify={async () => {}}
        onCancel={() => {}}
        onBack={() => {}}
      />
    );

    const input = screen.getByPlaceholderText('XXXX-XXXX');
    fireEvent.change(input, { target: { value: 'abcd' } });

    expect(input).toHaveValue('ABCD');
  });

  it('shows usage note', () => {
    render(
      <BackupCodeInput
        onVerify={async () => {}}
        onCancel={() => {}}
        onBack={() => {}}
      />
    );

    expect(screen.getByText(/each backup code can only be used once/i)).toBeInTheDocument();
  });
});
