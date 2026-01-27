'use client';

import { useState, useMemo } from 'react';
import {
  Download,
  Maximize2,
  X,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  ExternalLink,
  Table as TableIcon,
  Image as ImageIcon,
  BarChart3,
  Copy,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// =============================================================================
// Image Message
// =============================================================================

interface ImageMessageProps {
  src: string;
  alt?: string;
  caption?: string;
  width?: number;
  height?: number;
  className?: string;
}

/**
 * Rich image display in chat messages.
 * 
 * Features:
 * - Click to expand
 * - Zoom controls
 * - Download option
 */
export function ImageMessage({
  src,
  alt = 'Image',
  caption,
  width,
  height,
  className,
}: ImageMessageProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState(false);

  const handleDownload = async () => {
    try {
      const response = await fetch(src);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = alt || 'image';
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Image downloaded');
    } catch (e) {
      toast.error('Failed to download image');
    }
  };

  if (error) {
    return (
      <div className={cn('rounded-lg border bg-muted/50 p-4 text-center', className)}>
        <ImageIcon className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">Failed to load image</p>
      </div>
    );
  }

  return (
    <>
      <div className={cn('rounded-lg overflow-hidden border', className)}>
        <div className="relative group">
          <img
            src={src}
            alt={alt}
            width={width}
            height={height}
            className="w-full h-auto cursor-pointer"
            onClick={() => setIsOpen(true)}
            onError={() => setError(true)}
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
            <Button
              size="icon"
              variant="secondary"
              onClick={() => setIsOpen(true)}
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
        {caption && (
          <p className="px-3 py-2 text-sm text-muted-foreground bg-muted/50">
            {caption}
          </p>
        )}
      </div>

      {/* Fullscreen Dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 overflow-hidden">
          <DialogTitle className="sr-only">{alt}</DialogTitle>
          <div className="relative">
            {/* Controls */}
            <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
              <Button
                size="icon"
                variant="secondary"
                className="h-8 w-8"
                onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="px-2 text-sm">{Math.round(zoom * 100)}%</span>
              <Button
                size="icon"
                variant="secondary"
                className="h-8 w-8"
                onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button
                size="icon"
                variant="secondary"
                className="h-8 w-8"
                onClick={handleDownload}
              >
                <Download className="h-4 w-4" />
              </Button>
            </div>

            {/* Image */}
            <div className="overflow-auto max-h-[85vh]">
              <img
                src={src}
                alt={alt}
                style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }}
                className="transition-transform"
              />
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// =============================================================================
// Image Gallery
// =============================================================================

interface ImageGalleryProps {
  images: Array<{ src: string; alt?: string; caption?: string }>;
  className?: string;
}

/**
 * Gallery for multiple images
 */
export function ImageGallery({ images, className }: ImageGalleryProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  const currentImage = images[currentIndex];

  return (
    <>
      <div className={cn('grid grid-cols-2 gap-2 rounded-lg overflow-hidden', className)}>
        {images.slice(0, 4).map((image, index) => (
          <div
            key={index}
            className="relative aspect-square cursor-pointer group"
            onClick={() => {
              setCurrentIndex(index);
              setIsOpen(true);
            }}
          >
            <img
              src={image.src}
              alt={image.alt || `Image ${index + 1}`}
              className="w-full h-full object-cover"
            />
            {index === 3 && images.length > 4 && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                <span className="text-white text-lg font-medium">
                  +{images.length - 4}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Gallery Dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0">
          <DialogTitle className="sr-only">Image Gallery</DialogTitle>
          <div className="relative">
            {/* Navigation */}
            {images.length > 1 && (
              <>
                <Button
                  size="icon"
                  variant="secondary"
                  className="absolute left-2 top-1/2 -translate-y-1/2 z-10"
                  onClick={() => setCurrentIndex((i) => (i - 1 + images.length) % images.length)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  size="icon"
                  variant="secondary"
                  className="absolute right-2 top-1/2 -translate-y-1/2 z-10"
                  onClick={() => setCurrentIndex((i) => (i + 1) % images.length)}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </>
            )}

            {/* Image */}
            <img
              src={currentImage.src}
              alt={currentImage.alt || 'Gallery image'}
              className="max-h-[80vh] w-auto mx-auto"
            />

            {/* Caption & Counter */}
            <div className="p-4 text-center">
              {currentImage.caption && (
                <p className="text-sm text-muted-foreground mb-2">{currentImage.caption}</p>
              )}
              <span className="text-xs text-muted-foreground">
                {currentIndex + 1} / {images.length}
              </span>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// =============================================================================
// Data Table
// =============================================================================

interface DataTableProps {
  headers: string[];
  rows: (string | number)[][];
  caption?: string;
  sortable?: boolean;
  className?: string;
}

/**
 * Rich data table display in chat.
 * 
 * Features:
 * - Sortable columns
 * - Copy data
 * - Export to CSV
 */
export function DataTable({
  headers,
  rows,
  caption,
  sortable = true,
  className,
}: DataTableProps) {
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [copied, setCopied] = useState(false);

  const sortedRows = useMemo(() => {
    if (sortColumn === null) return rows;

    return [...rows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal).toLowerCase();
      const bStr = String(bVal).toLowerCase();
      return sortDirection === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr);
    });
  }, [rows, sortColumn, sortDirection]);

  const handleSort = (index: number) => {
    if (!sortable) return;
    if (sortColumn === index) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(index);
      setSortDirection('asc');
    }
  };

  const handleCopyTable = async () => {
    const csv = [headers.join('\t'), ...rows.map((row) => row.join('\t'))].join('\n');
    await navigator.clipboard.writeText(csv);
    setCopied(true);
    toast.success('Table copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportCSV = () => {
    const csv = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'data.csv';
    a.click();
    URL.revokeObjectURL(url);
    toast.success('CSV downloaded');
  };

  return (
    <div className={cn('rounded-lg border overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <TableIcon className="h-4 w-4" />
          <span>{rows.length} rows</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2"
            onClick={handleCopyTable}
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2"
            onClick={handleExportCSV}
          >
            <Download className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/30">
              {headers.map((header, index) => (
                <th
                  key={index}
                  className={cn(
                    'px-3 py-2 text-left font-medium',
                    sortable && 'cursor-pointer hover:bg-muted/50'
                  )}
                  onClick={() => handleSort(index)}
                >
                  <div className="flex items-center gap-1">
                    {header}
                    {sortColumn === index && (
                      <span className="text-xs">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={cn(
                  'border-b last:border-0',
                  rowIndex % 2 === 0 ? 'bg-background' : 'bg-muted/20'
                )}
              >
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="px-3 py-2">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Caption */}
      {caption && (
        <p className="px-3 py-2 text-xs text-muted-foreground border-t bg-muted/30">
          {caption}
        </p>
      )}
    </div>
  );
}

// =============================================================================
// Simple Chart (Bar Chart)
// =============================================================================

interface ChartData {
  label: string;
  value: number;
  color?: string;
}

interface SimpleChartProps {
  data: ChartData[];
  title?: string;
  type?: 'bar' | 'horizontal-bar';
  showValues?: boolean;
  className?: string;
}

/**
 * Simple chart visualization for chat messages.
 * 
 * For complex charts, integrate with a charting library.
 */
export function SimpleChart({
  data,
  title,
  type = 'bar',
  showValues = true,
  className,
}: SimpleChartProps) {
  const maxValue = Math.max(...data.map((d) => d.value));

  const defaultColors = [
    'bg-blue-500',
    'bg-green-500',
    'bg-yellow-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-cyan-500',
    'bg-orange-500',
    'bg-red-500',
  ];

  return (
    <div className={cn('rounded-lg border p-4', className)}>
      {/* Header */}
      {title && (
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
          <h4 className="font-medium">{title}</h4>
        </div>
      )}

      {/* Chart */}
      {type === 'bar' ? (
        <div className="flex items-end gap-2 h-40">
          {data.map((item, index) => {
            const height = (item.value / maxValue) * 100;
            return (
              <div key={index} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={cn(
                    'w-full rounded-t transition-all',
                    item.color || defaultColors[index % defaultColors.length]
                  )}
                  style={{ height: `${height}%` }}
                  title={`${item.label}: ${item.value}`}
                />
                {showValues && (
                  <span className="text-xs text-muted-foreground">{item.value}</span>
                )}
                <span className="text-xs text-muted-foreground truncate max-w-full">
                  {item.label}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((item, index) => {
            const width = (item.value / maxValue) * 100;
            return (
              <div key={index}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span>{item.label}</span>
                  {showValues && <span className="text-muted-foreground">{item.value}</span>}
                </div>
                <div className="h-4 bg-muted rounded-full overflow-hidden">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      item.color || defaultColors[index % defaultColors.length]
                    )}
                    style={{ width: `${width}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Link Preview
// =============================================================================

interface LinkPreviewProps {
  url: string;
  title?: string;
  description?: string;
  image?: string;
  siteName?: string;
  className?: string;
}

/**
 * Rich link preview card
 */
export function LinkPreview({
  url,
  title,
  description,
  image,
  siteName,
  className,
}: LinkPreviewProps) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        'block rounded-lg border overflow-hidden hover:bg-muted/50 transition-colors',
        className
      )}
    >
      <div className="flex">
        {image && (
          <div className="w-24 h-24 shrink-0">
            <img src={image} alt="" className="w-full h-full object-cover" />
          </div>
        )}
        <div className="p-3 flex-1 min-w-0">
          {siteName && (
            <span className="text-xs text-muted-foreground">{siteName}</span>
          )}
          {title && (
            <h4 className="font-medium text-sm line-clamp-1">{title}</h4>
          )}
          {description && (
            <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
              {description}
            </p>
          )}
          <div className="flex items-center gap-1 mt-2 text-xs text-primary">
            <ExternalLink className="h-3 w-3" />
            <span className="truncate">{new URL(url).hostname}</span>
          </div>
        </div>
      </div>
    </a>
  );
}

export default {
  ImageMessage,
  ImageGallery,
  DataTable,
  SimpleChart,
  LinkPreview,
};
