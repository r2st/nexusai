'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  FileText,
  Upload,
  Search,
  Trash2,
  Download,
  Eye,
  RefreshCw,
  FileUp,
  File,
  FileSpreadsheet,
  FileImage,
  Loader2,
  X,
  CheckCircle,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { documentsApi, type Document, type SearchResult } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { cn, formatFileSize, formatRelativeTime } from '@/lib/utils';
import { toast } from 'sonner';
import { FloatingAssistant } from '@/components/assistant';

type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

const getFileIcon = (mimeType: string) => {
  if (mimeType.includes('pdf')) return FileText;
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel'))
    return FileSpreadsheet;
  if (mimeType.includes('image')) return FileImage;
  return File;
};

const getStatusIcon = (status: DocumentStatus) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'processing':
      return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-yellow-500" />;
  }
};

const getStatusLabel = (status: DocumentStatus) => {
  switch (status) {
    case 'completed':
      return 'Ready';
    case 'processing':
      return 'Processing';
    case 'failed':
      return 'Failed';
    default:
      return 'Pending';
  }
};

export default function DocumentsPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  // Load documents
  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await documentsApi.list();
      setDocuments(data);
    } catch (error) {
      console.error('Failed to load documents:', error);
      toast.error('Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadDocuments();
    }
  }, [isAuthenticated, loadDocuments]);

  // Handle file upload
  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setIsUploading(true);
    const uploadPromises = Array.from(files).map(async (file) => {
      try {
        const doc = await documentsApi.upload(file);
        // Auto-process the document
        await documentsApi.process(doc.id);
        return doc;
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
        toast.error(`Failed to upload ${file.name}`);
        return null;
      }
    });

    const results = await Promise.all(uploadPromises);
    const successful = results.filter(Boolean) as Document[];

    if (successful.length > 0) {
      toast.success(`Uploaded ${successful.length} document(s)`);
      loadDocuments();
    }

    setIsUploading(false);
  };

  // Handle drag and drop
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    handleUpload(e.dataTransfer.files);
  };

  // Handle search
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const results = await documentsApi.search(searchQuery);
      setSearchResults(results);
      setShowSearch(true);
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  // Handle delete
  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await documentsApi.delete(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      toast.success('Document deleted');
    } catch (error) {
      console.error('Failed to delete document:', error);
      toast.error('Failed to delete document');
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <FileText className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Documents</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadDocuments}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Link href="/chat">
              <Button variant="ghost" size="sm">
                Go to Chat
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Upload Section */}
        <div
          className={cn(
            'relative mb-8 rounded-lg border-2 border-dashed p-8 text-center transition-colors',
            dragActive
              ? 'border-primary bg-primary/5'
              : 'border-muted-foreground/25 hover:border-muted-foreground/50'
          )}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="file-upload"
            className="hidden"
            multiple
            accept=".pdf,.doc,.docx,.txt,.md,.csv,.xlsx"
            onChange={(e) => handleUpload(e.target.files)}
          />

          {isUploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <p className="mt-4 text-lg font-medium">Uploading...</p>
            </div>
          ) : (
            <>
              <FileUp className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 text-lg font-medium">
                Drop files here or click to upload
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Supports PDF, Word, Text, Markdown, CSV, Excel
              </p>
              <Button
                className="mt-4"
                onClick={() => document.getElementById('file-upload')?.click()}
              >
                <Upload className="mr-2 h-4 w-4" />
                Select Files
              </Button>
            </>
          )}
        </div>

        {/* Search Section */}
        <div className="mb-8">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input
                placeholder="Search documents using natural language..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                className="pl-10"
                aria-label="Search documents"
              />
            </div>
            <Button onClick={handleSearch} disabled={isSearching}>
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Search'
              )}
            </Button>
          </div>
        </div>

        {/* Search Results */}
        {showSearch && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">
                Search Results ({searchResults.length})
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowSearch(false);
                  setSearchResults([]);
                  setSearchQuery('');
                }}
              >
                <X className="mr-2 h-4 w-4" />
                Clear
              </Button>
            </div>
            {searchResults.length === 0 ? (
              <p className="text-muted-foreground">No results found.</p>
            ) : (
              <div className="space-y-4">
                {searchResults.map((result) => (
                  <div
                    key={result.id}
                    className="rounded-lg border p-4 hover:bg-muted/50"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="h-4 w-4 text-primary" />
                          <span className="font-medium">{result.filename}</span>
                          <span className="text-xs text-muted-foreground">
                            Chunk {result.chunk_index + 1}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-3">
                          {result.content}
                        </p>
                      </div>
                      <div className="ml-4 text-right">
                        <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
                          {(result.similarity * 100).toFixed(0)}% match
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Documents List */}
        <section>
          <h2 className="text-lg font-semibold mb-4">
            Your Documents ({documents.length})
          </h2>

          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No documents yet</h3>
              <p className="mt-2 text-muted-foreground">
                Upload your first document to get started with RAG
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {documents.map((doc) => {
                const Icon = getFileIcon(doc.mime_type);
                return (
                  <div
                    key={doc.id}
                    className="rounded-lg border bg-card p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium truncate">
                          {doc.original_filename}
                        </h3>
                        <div className="flex items-center gap-2 mt-1">
                          {getStatusIcon(doc.status as DocumentStatus)}
                          <span className="text-xs text-muted-foreground">
                            {getStatusLabel(doc.status as DocumentStatus)}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                      <span>{formatFileSize(doc.file_size)}</span>
                      <span>{doc.chunk_count} chunks</span>
                      <span>{formatRelativeTime(doc.created_at)}</span>
                    </div>

                    <div className="mt-4 flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="flex-1"
                        onClick={() => setPreviewDoc(doc)}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Preview
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleDelete(doc.id)}
                        aria-label={`Delete ${doc.original_filename}`}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Quick Actions */}
        <section className="mt-12">
          <h2 className="text-lg font-semibold mb-4">What can you do?</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border p-4">
              <Upload className="h-8 w-8 text-primary mb-2" />
              <h3 className="font-medium">Upload Documents</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Upload PDFs, Word docs, and more for AI analysis
              </p>
            </div>
            <div className="rounded-lg border p-4">
              <Search className="h-8 w-8 text-primary mb-2" />
              <h3 className="font-medium">Semantic Search</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Find relevant content using natural language
              </p>
            </div>
            <div className="rounded-lg border p-4">
              <FileText className="h-8 w-8 text-primary mb-2" />
              <h3 className="font-medium">Chat with Documents</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Ask questions and get answers from your docs
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Document Preview Modal */}
      {previewDoc && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          role="dialog"
          aria-modal="true"
          aria-labelledby="doc-preview-title"
          onKeyDown={(e) => { if (e.key === 'Escape') setPreviewDoc(null); }}
        >
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setPreviewDoc(null)}
            aria-hidden="true"
          />
          <div className="relative z-10 w-full max-w-lg rounded-lg bg-background p-6 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 id="doc-preview-title" className="text-lg font-semibold">Document Details</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setPreviewDoc(null)}
                aria-label="Close"
              >
                <X className="h-4 w-4" aria-hidden="true" />
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-3">
                {(() => {
                  const Icon = getFileIcon(previewDoc.mime_type);
                  return (
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                  );
                })()}
                <div>
                  <p className="font-medium">{previewDoc.original_filename}</p>
                  <p className="text-sm text-muted-foreground">
                    {previewDoc.mime_type}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 rounded-lg border p-4">
                <div>
                  <p className="text-xs text-muted-foreground">File Size</p>
                  <p className="font-medium">
                    {formatFileSize(previewDoc.file_size)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Status</p>
                  <div className="flex items-center gap-1.5">
                    {getStatusIcon(previewDoc.status as DocumentStatus)}
                    <span className="font-medium">
                      {getStatusLabel(previewDoc.status as DocumentStatus)}
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Chunks</p>
                  <p className="font-medium">{previewDoc.chunk_count}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Uploaded</p>
                  <p className="font-medium">
                    {formatRelativeTime(previewDoc.created_at)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Type</p>
                  <p className="font-medium">{previewDoc.document_type}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">ID</p>
                  <p className="font-mono text-xs truncate">{previewDoc.id}</p>
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setPreviewDoc(null)}
                >
                  Close
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => {
                    handleDelete(previewDoc.id);
                    setPreviewDoc(null);
                  }}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <FloatingAssistant context="documents" />
    </div>
  );
}
