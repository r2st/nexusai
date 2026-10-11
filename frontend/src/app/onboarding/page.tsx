'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  Sparkles,
  Building2,
  Users,
  MessageSquare,
  FileText,
  Bot,
  Zap,
  ArrowRight,
  ArrowLeft,
  Check,
  Loader2,
  Github,
  Globe,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { organizationsApi, TenantContext, getApiErrorMessage } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

type OnboardingStep = 'welcome' | 'create-org' | 'invite-team' | 'use-case' | 'complete';

interface UseCase {
  id: string;
  title: string;
  description: string;
  icon: typeof MessageSquare;
  features: string[];
}

const useCases: UseCase[] = [
  {
    id: 'chat',
    title: 'AI Chat Assistant',
    description: 'Conversational AI for your team',
    icon: MessageSquare,
    features: ['Multi-model support', 'Team conversations', 'Custom prompts'],
  },
  {
    id: 'rag',
    title: 'Document Intelligence',
    description: 'Chat with your documents using RAG',
    icon: FileText,
    features: ['PDF & Word support', 'Semantic search', 'Knowledge base'],
  },
  {
    id: 'agents',
    title: 'AI Agents',
    description: 'Autonomous agents for complex tasks',
    icon: Bot,
    features: ['Custom agents', 'Tool integrations', 'Workflow automation'],
  },
  {
    id: 'devops',
    title: 'DevOps Intelligence',
    description: 'DORA metrics & engineering insights',
    icon: Zap,
    features: ['GitHub integration', 'DORA analysis', 'Performance tracking'],
  },
];

function OnboardingLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense fallback={<OnboardingLoading />}>
      <OnboardingContent />
    </Suspense>
  );
}

function OnboardingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isAuthenticated } = useAuthStore();
  
  const [step, setStep] = useState<OnboardingStep>('welcome');
  const [isLoading, setIsLoading] = useState(false);
  
  // Form state
  const [orgName, setOrgName] = useState('');
  const [orgSlug, setOrgSlug] = useState('');
  const [inviteEmails, setInviteEmails] = useState<string[]>(['']);
  const [selectedUseCases, setSelectedUseCases] = useState<string[]>([]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  // Check if coming to create new org
  useEffect(() => {
    if (searchParams.get('mode') === 'create-org') {
      setStep('create-org');
    }
  }, [searchParams]);

  // Auto-generate slug from org name
  useEffect(() => {
    if (orgName) {
      setOrgSlug(
        orgName
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-|-$/g, '')
      );
    }
  }, [orgName]);

  const handleCreateOrg = async () => {
    if (!orgName.trim()) {
      toast.error('Please enter an organization name');
      return;
    }

    setIsLoading(true);
    try {
      const org = await organizationsApi.create({
        name: orgName,
        slug: orgSlug || undefined,
      });
      
      // Set as current tenant
      TenantContext.setCurrentTenantId(org.id);
      
      toast.success('Organization created!');
      setStep('invite-team');
    } catch (error: unknown) {
      console.error('Failed to create organization:', error);
      toast.error(getApiErrorMessage(error, 'Failed to create organization'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleInviteTeam = async () => {
    const validEmails = inviteEmails.filter((e) => e.trim() && e.includes('@'));
    
    if (validEmails.length > 0) {
      setIsLoading(true);
      const orgId = TenantContext.getCurrentTenantId();
      
      if (orgId) {
        try {
          await Promise.all(
            validEmails.map((email) =>
              organizationsApi.inviteMember(orgId, email, 'member')
            )
          );
          toast.success(`Invited ${validEmails.length} team member(s)`);
        } catch (error) {
          console.error('Failed to invite members:', error);
          toast.error('Some invitations failed to send');
        }
      }
      setIsLoading(false);
    }
    
    setStep('use-case');
  };

  const handleComplete = () => {
    // Navigate based on selected use cases
    if (selectedUseCases.includes('chat')) {
      router.push('/chat');
    } else if (selectedUseCases.includes('rag')) {
      router.push('/documents');
    } else if (selectedUseCases.includes('agents')) {
      router.push('/agents');
    } else if (selectedUseCases.includes('devops')) {
      router.push('/devops');
    } else {
      router.push('/chat');
    }
  };

  const addInviteField = () => {
    setInviteEmails([...inviteEmails, '']);
  };

  const updateInviteEmail = (index: number, value: string) => {
    const updated = [...inviteEmails];
    updated[index] = value;
    setInviteEmails(updated);
  };

  const toggleUseCase = (id: string) => {
    setSelectedUseCases((prev) =>
      prev.includes(id)
        ? prev.filter((c) => c !== id)
        : [...prev, id]
    );
  };

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Progress */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            {['welcome', 'create-org', 'invite-team', 'use-case', 'complete'].map((s, i) => (
              <div
                key={s}
                className={cn(
                  'flex items-center justify-center h-8 w-8 rounded-full text-sm font-medium transition-colors',
                  step === s
                    ? 'bg-primary text-primary-foreground'
                    : ['welcome', 'create-org', 'invite-team', 'use-case', 'complete'].indexOf(step) > i
                    ? 'bg-primary/20 text-primary'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {['welcome', 'create-org', 'invite-team', 'use-case', 'complete'].indexOf(step) > i ? (
                  <Check className="h-4 w-4" />
                ) : (
                  i + 1
                )}
              </div>
            ))}
          </div>
          <div className="h-1 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{
                width: `${
                  (['welcome', 'create-org', 'invite-team', 'use-case', 'complete'].indexOf(step) / 4) * 100
                }%`,
              }}
            />
          </div>
        </div>

        {/* Content */}
        <div className="rounded-xl border bg-card shadow-lg p-8">
          {/* Welcome Step */}
          {step === 'welcome' && (
            <div className="text-center">
              <div className="flex justify-center mb-6">
                <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <Sparkles className="h-8 w-8 text-primary" />
                </div>
              </div>
              <h1 className="text-2xl font-bold mb-2">
                Welcome to NexusAI{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}!
              </h1>
              <p className="text-muted-foreground mb-8">
                Let&apos;s get you set up in just a few steps. You&apos;ll be chatting with AI in no time.
              </p>
              
              <div className="grid gap-4 mb-8">
                <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50 text-left">
                  <Building2 className="h-6 w-6 text-primary shrink-0" />
                  <div>
                    <h3 className="font-medium">Create your workspace</h3>
                    <p className="text-sm text-muted-foreground">
                      Set up your organization for team collaboration
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50 text-left">
                  <Users className="h-6 w-6 text-primary shrink-0" />
                  <div>
                    <h3 className="font-medium">Invite your team</h3>
                    <p className="text-sm text-muted-foreground">
                      Bring colleagues to collaborate together
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50 text-left">
                  <Zap className="h-6 w-6 text-primary shrink-0" />
                  <div>
                    <h3 className="font-medium">Choose your tools</h3>
                    <p className="text-sm text-muted-foreground">
                      Select the AI features that fit your needs
                    </p>
                  </div>
                </div>
              </div>

              <Button size="lg" onClick={() => setStep('create-org')}>
                Get Started
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          )}

          {/* Create Organization Step */}
          {step === 'create-org' && (
            <div>
              <div className="text-center mb-8">
                <div className="flex justify-center mb-4">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <Building2 className="h-6 w-6 text-primary" />
                  </div>
                </div>
                <h1 className="text-2xl font-bold mb-2">Create your workspace</h1>
                <p className="text-muted-foreground">
                  Your organization is where your team collaborates
                </p>
              </div>

              <div className="space-y-4 mb-8">
                <div>
                  <label className="text-sm font-medium">Organization Name</label>
                  <Input
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="e.g., Acme Inc."
                    className="mt-1"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">URL Slug</label>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm text-muted-foreground">nexusai.com/</span>
                    <Input
                      value={orgSlug}
                      onChange={(e) => setOrgSlug(e.target.value)}
                      placeholder="acme"
                      className="flex-1"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Used for your team&apos;s unique URL
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep('welcome')}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleCreateOrg}
                  disabled={isLoading || !orgName.trim()}
                >
                  {isLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : null}
                  Create Organization
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Invite Team Step */}
          {step === 'invite-team' && (
            <div>
              <div className="text-center mb-8">
                <div className="flex justify-center mb-4">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <Users className="h-6 w-6 text-primary" />
                  </div>
                </div>
                <h1 className="text-2xl font-bold mb-2">Invite your team</h1>
                <p className="text-muted-foreground">
                  Collaboration is better together (you can skip this for now)
                </p>
              </div>

              <div className="space-y-3 mb-6">
                {inviteEmails.map((email, index) => (
                  <Input
                    key={index}
                    type="email"
                    value={email}
                    onChange={(e) => updateInviteEmail(index, e.target.value)}
                    placeholder="colleague@company.com"
                  />
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={addInviteField}
                  className="w-full"
                >
                  + Add another
                </Button>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep('create-org')}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setStep('use-case')}
                >
                  Skip
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleInviteTeam}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : null}
                  Send Invites
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Use Case Step */}
          {step === 'use-case' && (
            <div>
              <div className="text-center mb-8">
                <div className="flex justify-center mb-4">
                  <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <Zap className="h-6 w-6 text-primary" />
                  </div>
                </div>
                <h1 className="text-2xl font-bold mb-2">What will you use NexusAI for?</h1>
                <p className="text-muted-foreground">
                  Select all that apply – we&apos;ll customize your experience
                </p>
              </div>

              <div className="grid gap-3 mb-8">
                {useCases.map((useCase) => {
                  const Icon = useCase.icon;
                  const isSelected = selectedUseCases.includes(useCase.id);
                  
                  return (
                    <button
                      key={useCase.id}
                      onClick={() => toggleUseCase(useCase.id)}
                      className={cn(
                        'flex items-start gap-4 p-4 rounded-lg border text-left transition-colors',
                        isSelected
                          ? 'border-primary bg-primary/5'
                          : 'hover:bg-muted/50'
                      )}
                    >
                      <div
                        className={cn(
                          'h-10 w-10 rounded-lg flex items-center justify-center shrink-0',
                          isSelected ? 'bg-primary/10' : 'bg-muted'
                        )}
                      >
                        <Icon
                          className={cn(
                            'h-5 w-5',
                            isSelected ? 'text-primary' : 'text-muted-foreground'
                          )}
                        />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium">{useCase.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          {useCase.description}
                        </p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {useCase.features.map((feature) => (
                            <span
                              key={feature}
                              className="text-xs bg-muted px-2 py-0.5 rounded"
                            >
                              {feature}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div
                        className={cn(
                          'h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0',
                          isSelected ? 'border-primary bg-primary' : 'border-muted-foreground'
                        )}
                      >
                        {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
                      </div>
                    </button>
                  );
                })}
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep('invite-team')}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button className="flex-1" onClick={() => setStep('complete')}>
                  Continue
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Complete Step */}
          {step === 'complete' && (
            <div className="text-center">
              <div className="flex justify-center mb-6">
                <div className="h-16 w-16 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                  <Check className="h-8 w-8 text-green-600 dark:text-green-400" />
                </div>
              </div>
              <h1 className="text-2xl font-bold mb-2">You&apos;re all set!</h1>
              <p className="text-muted-foreground mb-8">
                Your workspace is ready. Let&apos;s start exploring NexusAI.
              </p>

              <div className="grid gap-3 mb-8">
                <Link href="/chat" className="block">
                  <Button variant="outline" className="w-full justify-start h-auto py-4">
                    <MessageSquare className="h-5 w-5 mr-3" />
                    <div className="text-left">
                      <p className="font-medium">Start a conversation</p>
                      <p className="text-xs text-muted-foreground">
                        Chat with AI models
                      </p>
                    </div>
                  </Button>
                </Link>
                <Link href="/documents" className="block">
                  <Button variant="outline" className="w-full justify-start h-auto py-4">
                    <FileText className="h-5 w-5 mr-3" />
                    <div className="text-left">
                      <p className="font-medium">Upload documents</p>
                      <p className="text-xs text-muted-foreground">
                        Build your knowledge base
                      </p>
                    </div>
                  </Button>
                </Link>
                <Link href="/integrations" className="block">
                  <Button variant="outline" className="w-full justify-start h-auto py-4">
                    <Globe className="h-5 w-5 mr-3" />
                    <div className="text-left">
                      <p className="font-medium">Connect integrations</p>
                      <p className="text-xs text-muted-foreground">
                        Link GitHub, Slack, and more
                      </p>
                    </div>
                  </Button>
                </Link>
              </div>

              <Button size="lg" onClick={handleComplete}>
                Go to Dashboard
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {/* Skip Link */}
        {step !== 'complete' && (
          <div className="text-center mt-4">
            <button
              onClick={() => router.push('/chat')}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Skip onboarding and go to chat
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
