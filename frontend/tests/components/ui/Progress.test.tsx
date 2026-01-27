/**
 * Progress Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Progress } from '@/components/ui/progress';

describe('Progress', () => {
  it('renders progress bar', () => {
    render(<Progress value={50} data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    expect(progress).toBeInTheDocument();
  });

  it('has correct base styles', () => {
    render(<Progress value={50} data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    expect(progress).toHaveClass('relative', 'h-4', 'w-full', 'overflow-hidden', 'rounded-full', 'bg-secondary');
  });

  it('applies custom className', () => {
    render(<Progress value={50} className="custom-progress" data-testid="progress" />);
    expect(screen.getByTestId('progress')).toHaveClass('custom-progress');
  });

  it('contains indicator element', () => {
    render(<Progress value={50} data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    const indicator = progress.firstChild as HTMLElement;
    expect(indicator).toHaveClass('bg-primary');
  });

  it('handles undefined value', () => {
    render(<Progress data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    expect(progress).toBeInTheDocument();
  });
});

describe('Progress Visual States', () => {
  it('renders empty state (0%)', () => {
    render(<Progress value={0} data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    const indicator = progress.firstChild as HTMLElement;
    expect(indicator).toHaveStyle({ transform: 'translateX(-100%)' });
  });

  it('renders half-filled state (50%)', () => {
    render(<Progress value={50} data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    const indicator = progress.firstChild as HTMLElement;
    expect(indicator).toHaveStyle({ transform: 'translateX(-50%)' });
  });

  it('renders full state (100%)', () => {
    render(<Progress value={100} data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    const indicator = progress.firstChild as HTMLElement;
    expect(indicator).toHaveStyle({ transform: 'translateX(-0%)' });
  });

  it('renders quarter filled (25%)', () => {
    render(<Progress value={25} data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    const indicator = progress.firstChild as HTMLElement;
    expect(indicator).toHaveStyle({ transform: 'translateX(-75%)' });
  });

  it('renders three quarters filled (75%)', () => {
    render(<Progress value={75} data-testid="progress" />);
    const progress = screen.getByTestId('progress');
    const indicator = progress.firstChild as HTMLElement;
    expect(indicator).toHaveStyle({ transform: 'translateX(-25%)' });
  });
});

describe('Progress Use Cases', () => {
  it('renders file upload progress', () => {
    const uploadProgress = 67;
    render(
      <div>
        <p>Uploading... {uploadProgress}%</p>
        <Progress value={uploadProgress} data-testid="upload-progress" />
      </div>
    );

    expect(screen.getByText('Uploading... 67%')).toBeInTheDocument();
    const progress = screen.getByTestId('upload-progress');
    const indicator = progress.firstChild as HTMLElement;
    expect(indicator).toHaveStyle({ transform: 'translateX(-33%)' });
  });

  it('renders loading progress (indeterminate)', () => {
    render(<Progress value={undefined} data-testid="loading" />);
    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });

  it('renders step progress', () => {
    const currentStep = 2;
    const totalSteps = 5;
    const progressValue = (currentStep / totalSteps) * 100;

    render(
      <div>
        <p>Step {currentStep} of {totalSteps}</p>
        <Progress value={progressValue} data-testid="step-progress" />
      </div>
    );

    expect(screen.getByText('Step 2 of 5')).toBeInTheDocument();
    const progress = screen.getByTestId('step-progress');
    const indicator = progress.firstChild as HTMLElement;
    expect(indicator).toHaveStyle({ transform: 'translateX(-60%)' });
  });
});
