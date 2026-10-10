'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Check,
  Sparkles,
  Zap,
  Building2,
  ArrowRight,
  HelpCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface PricingTier {
  name: string;
  description: string;
  price: number | null;
  priceLabel?: string;
  features: string[];
  highlighted?: boolean;
  cta: string;
  icon: typeof Sparkles;
}

const tiers: PricingTier[] = [
  {
    name: 'Free',
    description: 'For individuals getting started with AI',
    price: 0,
    features: [
      'Up to 3 projects',
      '5 team members',
      '100 AI conversations/month',
      '10 document uploads',
      'Community support',
      'Basic analytics',
    ],
    cta: 'Get Started',
    icon: Sparkles,
  },
  {
    name: 'Pro',
    description: 'For growing teams and professionals',
    price: 29,
    features: [
      'Unlimited projects',
      '25 team members',
      'Unlimited AI conversations',
      '500 document uploads',
      'Priority email support',
      'Advanced analytics',
      'Custom AI agents',
      'API access',
      'DORA metrics',
    ],
    highlighted: true,
    cta: 'Start Free Trial',
    icon: Zap,
  },
  {
    name: 'Enterprise',
    description: 'For large organizations with custom needs',
    price: null,
    priceLabel: 'Custom',
    features: [
      'Everything in Pro',
      'Unlimited team members',
      'Unlimited storage',
      'Dedicated support',
      'SLA guarantees',
      'SSO/SAML',
      'Custom integrations',
      'On-premise option',
      'Advanced security',
      'Custom training',
    ],
    cta: 'Contact Sales',
    icon: Building2,
  },
];

const faqs = [
  {
    question: 'Can I try Pro features before paying?',
    answer:
      'Yes! We offer a 14-day free trial of Pro features. No credit card required to start.',
  },
  {
    question: 'What happens when my trial ends?',
    answer:
      "You'll be downgraded to the Free tier. Your data is safe - you can upgrade anytime to regain access to Pro features.",
  },
  {
    question: 'Can I change plans later?',
    answer:
      'Absolutely. You can upgrade, downgrade, or cancel your subscription at any time from your account settings.',
  },
  {
    question: 'What payment methods do you accept?',
    answer:
      'We accept all major credit cards, PayPal, and for Enterprise customers, we also support invoicing.',
  },
  {
    question: 'Is there a discount for annual billing?',
    answer:
      'Yes! Annual billing saves you 20% compared to monthly billing. Contact us for Enterprise pricing.',
  },
];

export default function PricingPage() {
  const router = useRouter();
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const getPrice = (basePrice: number | null) => {
    if (basePrice === null) return null;
    if (basePrice === 0) return 0;
    return billingCycle === 'annual' ? Math.round(basePrice * 0.8) : basePrice;
  };

  const handleSelectPlan = (tier: PricingTier) => {
    if (tier.name === 'Enterprise') {
      window.location.href = 'mailto:sales@nexusai.com?subject=Enterprise%20Inquiry';
    } else if (tier.name === 'Free') {
      router.push('/register');
    } else {
      router.push('/start-trial');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted">
      {/* Header */}
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">NexusAI</span>
          </Link>
          <nav className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Login
            </Link>
            <Link href="/register">
              <Button size="sm">Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-16">
        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Simple, transparent pricing
          </h1>
          <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
            Choose the plan that fits your needs. Start free and scale as you grow.
          </p>
        </div>

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-4 mb-12">
          <span
            className={cn(
              'text-sm font-medium',
              billingCycle === 'monthly' ? 'text-foreground' : 'text-muted-foreground'
            )}
          >
            Monthly
          </span>
          <button
            onClick={() =>
              setBillingCycle(billingCycle === 'monthly' ? 'annual' : 'monthly')
            }
            className={cn(
              'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
              billingCycle === 'annual' ? 'bg-primary' : 'bg-muted'
            )}
          >
            <span
              className={cn(
                'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                billingCycle === 'annual' ? 'translate-x-6' : 'translate-x-1'
              )}
            />
          </button>
          <span
            className={cn(
              'text-sm font-medium',
              billingCycle === 'annual' ? 'text-foreground' : 'text-muted-foreground'
            )}
          >
            Annual
            <span className="ml-1.5 inline-flex items-center rounded-full bg-green-100 dark:bg-green-900 px-2 py-0.5 text-xs font-medium text-green-700 dark:text-green-300">
              Save 20%
            </span>
          </span>
        </div>

        {/* Pricing Cards */}
        <div className="grid gap-8 lg:grid-cols-3 max-w-6xl mx-auto">
          {tiers.map((tier) => {
            const Icon = tier.icon;
            const price = getPrice(tier.price);

            return (
              <div
                key={tier.name}
                className={cn(
                  'relative rounded-2xl border bg-card p-8',
                  tier.highlighted &&
                    'border-primary shadow-lg ring-1 ring-primary'
                )}
              >
                {tier.highlighted && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center rounded-full bg-primary px-4 py-1 text-sm font-medium text-primary-foreground">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-3 mb-4">
                  <div
                    className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-lg',
                      tier.highlighted ? 'bg-primary/10' : 'bg-muted'
                    )}
                  >
                    <Icon
                      className={cn(
                        'h-5 w-5',
                        tier.highlighted ? 'text-primary' : 'text-muted-foreground'
                      )}
                    />
                  </div>
                  <h3 className="text-xl font-semibold">{tier.name}</h3>
                </div>

                <p className="text-sm text-muted-foreground mb-6">
                  {tier.description}
                </p>

                <div className="mb-6">
                  {price !== null ? (
                    <>
                      <span className="text-4xl font-bold">${price}</span>
                      <span className="text-muted-foreground">/month</span>
                      {billingCycle === 'annual' && tier.price !== 0 && (
                        <p className="text-sm text-muted-foreground mt-1">
                          Billed annually (${price * 12}/year)
                        </p>
                      )}
                    </>
                  ) : (
                    <span className="text-4xl font-bold">{tier.priceLabel}</span>
                  )}
                </div>

                <Button
                  className="w-full mb-6"
                  variant={tier.highlighted ? 'default' : 'outline'}
                  onClick={() => handleSelectPlan(tier)}
                >
                  {tier.cta}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>

                <ul className="space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <Check className="h-5 w-5 shrink-0 text-green-500" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>

        {/* FAQ Section */}
        <section className="mt-24 max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-8">
            Frequently Asked Questions
          </h2>
          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div key={index} className="rounded-lg border bg-card">
                <button
                  className="flex w-full items-center justify-between p-4 text-left"
                  onClick={() =>
                    setExpandedFaq(expandedFaq === index ? null : index)
                  }
                >
                  <span className="font-medium">{faq.question}</span>
                  <HelpCircle
                    className={cn(
                      'h-5 w-5 text-muted-foreground transition-transform',
                      expandedFaq === index && 'rotate-180'
                    )}
                  />
                </button>
                {expandedFaq === index && (
                  <div className="px-4 pb-4 text-sm text-muted-foreground">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="mt-24 text-center">
          <div className="rounded-2xl bg-primary/5 border border-primary/10 p-12">
            <h2 className="text-2xl font-bold mb-4">
              Ready to supercharge your team?
            </h2>
            <p className="text-muted-foreground mb-6 max-w-xl mx-auto">
              Join thousands of teams already using NexusAI to build better
              software faster.
            </p>
            <div className="flex items-center justify-center gap-4">
              <Link href="/start-trial">
                <Button size="lg">
                  Start Free Trial
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/chat">
                <Button variant="outline" size="lg">
                  Try Demo
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="mt-24 border-t py-8">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              © 2025 NexusAI Contributors.
            </p>
            <div className="flex items-center gap-6">
              <Link
                href="/terms"
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Terms
              </Link>
              <Link
                href="/privacy"
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Privacy
              </Link>
              <a
                href="mailto:support@nexusai.com"
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Contact
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
