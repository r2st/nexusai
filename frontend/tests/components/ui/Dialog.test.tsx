/**
 * Dialog Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from '@/components/ui/dialog';

describe('Dialog', () => {
  it('renders trigger button', () => {
    render(
      <Dialog>
        <DialogTrigger>Open Dialog</DialogTrigger>
        <DialogContent>
          <DialogTitle>Test Dialog</DialogTitle>
          <DialogDescription>Dialog description</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByText('Open Dialog')).toBeInTheDocument();
  });

  it('opens dialog when trigger is clicked', async () => {
    render(
      <Dialog>
        <DialogTrigger>Open Dialog</DialogTrigger>
        <DialogContent>
          <DialogTitle>Test Dialog</DialogTitle>
          <DialogDescription>Dialog content</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    fireEvent.click(screen.getByText('Open Dialog'));
    
    expect(await screen.findByText('Test Dialog')).toBeInTheDocument();
    expect(screen.getByText('Dialog content')).toBeInTheDocument();
  });

  it('renders with controlled open state', () => {
    render(
      <Dialog open={true}>
        <DialogContent>
          <DialogTitle>Controlled Dialog</DialogTitle>
          <DialogDescription>Description</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByText('Controlled Dialog')).toBeInTheDocument();
  });

  it('calls onOpenChange when state changes', () => {
    const onOpenChange = vi.fn();
    
    render(
      <Dialog open={false} onOpenChange={onOpenChange}>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Test</DialogTitle>
          <DialogDescription>Desc</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    fireEvent.click(screen.getByText('Open'));
    expect(onOpenChange).toHaveBeenCalledWith(true);
  });
});

describe('DialogHeader', () => {
  it('renders with correct layout', () => {
    render(
      <Dialog open={true}>
        <DialogContent>
          <DialogHeader data-testid="header">
            <DialogTitle>Title</DialogTitle>
            <DialogDescription>Description</DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByTestId('header')).toHaveClass('flex', 'flex-col', 'space-y-1.5');
  });
});

describe('DialogFooter', () => {
  it('renders with correct layout', () => {
    render(
      <Dialog open={true}>
        <DialogContent>
          <DialogTitle>Test</DialogTitle>
          <DialogDescription>Desc</DialogDescription>
          <DialogFooter data-testid="footer">
            <button>Cancel</button>
            <button>Save</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );

    const footer = screen.getByTestId('footer');
    expect(footer).toHaveClass('flex', 'flex-col-reverse');
  });
});

describe('DialogTitle', () => {
  it('renders as heading', () => {
    render(
      <Dialog open={true}>
        <DialogContent>
          <DialogTitle>Dialog Title</DialogTitle>
          <DialogDescription>Desc</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    const title = screen.getByText('Dialog Title');
    expect(title).toHaveClass('text-lg', 'font-semibold');
  });
});

describe('DialogDescription', () => {
  it('renders with muted color', () => {
    render(
      <Dialog open={true}>
        <DialogContent>
          <DialogTitle>Test</DialogTitle>
          <DialogDescription>Description text</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByText('Description text')).toHaveClass('text-sm', 'text-muted-foreground');
  });
});

describe('DialogClose', () => {
  it('closes dialog when clicked', () => {
    const onOpenChange = vi.fn();
    
    render(
      <Dialog open={true} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogTitle>Test</DialogTitle>
          <DialogDescription>Desc</DialogDescription>
          <DialogClose data-testid="close-btn">Close Dialog</DialogClose>
        </DialogContent>
      </Dialog>
    );

    fireEvent.click(screen.getByTestId('close-btn'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});

describe('Dialog Accessibility', () => {
  it('has correct role attribute', () => {
    render(
      <Dialog open={true}>
        <DialogContent>
          <DialogTitle>Accessible Dialog</DialogTitle>
          <DialogDescription>Description for screen readers</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
  });

  it('contains focusable elements', async () => {
    render(
      <Dialog open={true}>
        <DialogContent>
          <DialogTitle>Focus Test</DialogTitle>
          <DialogDescription>Test description</DialogDescription>
          <input data-testid="input1" />
          <input data-testid="input2" />
        </DialogContent>
      </Dialog>
    );

    const input1 = screen.getByTestId('input1');
    const input2 = screen.getByTestId('input2');
    
    expect(input1).toBeInTheDocument();
    expect(input2).toBeInTheDocument();
  });
});
