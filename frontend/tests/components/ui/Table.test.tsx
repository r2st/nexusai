/**
 * Table Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
} from '@/components/ui/table';

describe('Table', () => {
  it('renders table with default styles', () => {
    render(
      <Table data-testid="table">
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    const table = screen.getByTestId('table');
    expect(table).toBeInTheDocument();
    expect(table.tagName).toBe('TABLE');
    expect(table).toHaveClass('w-full', 'caption-bottom', 'text-sm');
  });

  it('applies custom className', () => {
    render(
      <Table className="custom-table">
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    expect(screen.getByRole('table')).toHaveClass('custom-table');
  });
});

describe('TableHeader', () => {
  it('renders thead element', () => {
    render(
      <Table>
        <TableHeader data-testid="header">
          <TableRow>
            <TableHead>Header</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    const header = screen.getByTestId('header');
    expect(header.tagName).toBe('THEAD');
    expect(header).toHaveClass('[&_tr]:border-b');
  });
});

describe('TableBody', () => {
  it('renders tbody element', () => {
    render(
      <Table>
        <TableBody data-testid="body">
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    const body = screen.getByTestId('body');
    expect(body.tagName).toBe('TBODY');
    expect(body).toHaveClass('[&_tr:last-child]:border-0');
  });
});

describe('TableFooter', () => {
  it('renders tfoot element', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
        <TableFooter data-testid="footer">
          <TableRow>
            <TableCell>Footer</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    );

    const footer = screen.getByTestId('footer');
    expect(footer.tagName).toBe('TFOOT');
    expect(footer).toHaveClass('border-t', 'bg-muted/50', 'font-medium');
  });
});

describe('TableRow', () => {
  it('renders tr element with hover styles', () => {
    render(
      <Table>
        <TableBody>
          <TableRow data-testid="row">
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    const row = screen.getByTestId('row');
    expect(row.tagName).toBe('TR');
    expect(row).toHaveClass('border-b', 'transition-colors', 'hover:bg-muted/50');
  });

  it('applies data-state for selected rows', () => {
    render(
      <Table>
        <TableBody>
          <TableRow data-testid="row" data-state="selected">
            <TableCell>Selected Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    const row = screen.getByTestId('row');
    expect(row).toHaveAttribute('data-state', 'selected');
    expect(row).toHaveClass('data-[state=selected]:bg-muted');
  });
});

describe('TableHead', () => {
  it('renders th element', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Header</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    const head = screen.getByText('Header');
    expect(head.tagName).toBe('TH');
    expect(head).toHaveClass('h-12', 'px-4', 'text-left', 'font-medium', 'text-muted-foreground');
  });
});

describe('TableCell', () => {
  it('renders td element', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell>Cell Content</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    const cell = screen.getByText('Cell Content');
    expect(cell.tagName).toBe('TD');
    expect(cell).toHaveClass('p-4', 'align-middle');
  });
});

describe('TableCaption', () => {
  it('renders caption element', () => {
    render(
      <Table>
        <TableCaption>Table caption text</TableCaption>
        <TableBody>
          <TableRow>
            <TableCell>Cell</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    const caption = screen.getByText('Table caption text');
    expect(caption.tagName).toBe('CAPTION');
    expect(caption).toHaveClass('mt-4', 'text-sm', 'text-muted-foreground');
  });
});

describe('Table Composition', () => {
  it('renders complete table with all sections', () => {
    const data = [
      { id: 1, name: 'Item 1', value: 100 },
      { id: 2, name: 'Item 2', value: 200 },
    ];

    render(
      <Table>
        <TableCaption>A list of items</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Value</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((item) => (
            <TableRow key={item.id}>
              <TableCell>{item.id}</TableCell>
              <TableCell>{item.name}</TableCell>
              <TableCell>{item.value}</TableCell>
            </TableRow>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell colSpan={2}>Total</TableCell>
            <TableCell>300</TableCell>
          </TableRow>
        </TableFooter>
      </Table>
    );

    expect(screen.getByText('A list of items')).toBeInTheDocument();
    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
    expect(screen.getByText('Total')).toBeInTheDocument();
    expect(screen.getByText('300')).toBeInTheDocument();
  });
});
