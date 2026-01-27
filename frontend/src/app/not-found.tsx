import Link from 'next/link';
import { Home, ArrowLeft, Search, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <div className="text-center max-w-md">
        {/* 404 Illustration */}
        <div className="relative mx-auto w-48 h-48 mb-8">
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-[120px] font-bold text-muted-foreground/20">
              404
            </span>
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center animate-pulse">
              <Search className="h-10 w-10 text-primary" />
            </div>
          </div>
        </div>

        <h1 className="text-3xl font-bold mb-2">Page Not Found</h1>
        <p className="text-muted-foreground mb-8">
          Sorry, we couldn&apos;t find the page you&apos;re looking for. 
          It might have been moved or doesn&apos;t exist.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/">
            <Button>
              <Home className="mr-2 h-4 w-4" />
              Go Home
            </Button>
          </Link>
          <Link href="/chat">
            <Button variant="outline">
              <MessageSquare className="mr-2 h-4 w-4" />
              Start Chatting
            </Button>
          </Link>
        </div>

        {/* Helpful Links */}
        <div className="mt-12 pt-8 border-t">
          <p className="text-sm text-muted-foreground mb-4">
            Here are some helpful links:
          </p>
          <div className="flex flex-wrap justify-center gap-4 text-sm">
            <Link
              href="/chat"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              Chat
            </Link>
            <Link
              href="/documents"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              Documents
            </Link>
            <Link
              href="/agents"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              Agents
            </Link>
            <Link
              href="/settings"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              Settings
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
