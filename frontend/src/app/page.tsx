'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Trophy, Target, BarChart3, Zap, Award, Smartphone } from 'lucide-react';

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="container-mobile py-10 space-y-6">
        <Skeleton className="h-8 w-48 mx-auto" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-4 w-3/4 mx-auto" />
        <Skeleton className="h-10 w-40 mx-auto" />
      </div>
    );
  }

  return (
    <div className="min-h-[100dvh] bg-background">
      {/* Hero Section */}
      <section className="container-mobile pt-16 pb-12 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs text-muted-foreground mb-6">
          <Trophy className="h-3.5 w-3.5 text-primary" />
          <span>Women&apos;s Premier League 2025</span>
        </div>

        <h1 className="text-3xl font-bold tracking-tight mb-3">
          Your Fantasy Cricket
          <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent"> League Awaits</span>
        </h1>

        <p className="text-sm text-muted-foreground max-w-md mx-auto mb-8 leading-relaxed">
          Join thousands of cricket fans predicting match outcomes, competing with friends,
          and climbing leaderboards. Turn your cricket knowledge into glory!
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-10">
          <Link href="/signup">
            <Button size="lg" className="w-full sm:w-auto">
              Start Playing Free
            </Button>
          </Link>
          <Link href="/login">
            <Button variant="outline" size="lg" className="w-full sm:w-auto">
              Sign In
            </Button>
          </Link>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: '1000+', label: 'Active Players' },
            { value: '50+', label: 'Live Leagues' },
            { value: '5000+', label: 'Predictions Made' },
          ].map((stat) => (
            <div key={stat.label} className="rounded-lg border border-border bg-card p-3">
              <div className="text-lg font-bold text-foreground">{stat.value}</div>
              <div className="text-[10px] text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features Section */}
      <section className="container-mobile py-12">
        <div className="text-center mb-8">
          <h2 className="text-xl font-bold mb-2">Everything You Need to Dominate</h2>
          <p className="text-sm text-muted-foreground">
            Powerful features that make fantasy cricket exciting and competitive
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            { icon: Trophy, title: 'Private Leagues', desc: 'Create exclusive leagues with custom rules. Invite friends to compete.' },
            { icon: Target, title: 'Smart Predictions', desc: 'Predict match winners, top scorers, and performances. Earn points.' },
            { icon: BarChart3, title: 'Live Leaderboards', desc: 'Track your rank in real-time against competitors with detailed stats.' },
            { icon: Zap, title: 'Instant Updates', desc: 'Real-time match updates and automatic score calculations.' },
            { icon: Award, title: 'Achievement System', desc: 'Unlock badges and rewards as you improve your predictions.' },
            { icon: Smartphone, title: 'Mobile Optimized', desc: 'Play anywhere, anytime. Fully responsive mobile experience.' },
          ].map((feature) => (
            <Card key={feature.title} className="border-border bg-card">
              <CardContent className="p-4 space-y-2">
                <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center">
                  <feature.icon className="h-4 w-4 text-primary" />
                </div>
                <h3 className="text-sm font-semibold">{feature.title}</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">{feature.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* How It Works Section */}
      <section className="container-mobile py-12">
        <div className="text-center mb-8">
          <h2 className="text-xl font-bold mb-2">How It Works</h2>
          <p className="text-sm text-muted-foreground">
            Get started in three simple steps
          </p>
        </div>

        <div className="space-y-4">
          {[
            { step: '1', title: 'Create Your Account', desc: 'Sign up in seconds. No payment required. Start with a free account.' },
            { step: '2', title: 'Join or Create a League', desc: 'Browse public leagues or create a private one. Invite your friends with a simple code.' },
            { step: '3', title: 'Make Predictions & Win', desc: 'Predict match outcomes before each game. Earn points and climb the leaderboard!' },
          ].map((item) => (
            <Card key={item.step} className="border-border bg-card">
              <CardContent className="flex items-start gap-4 p-4">
                <div className="h-10 w-10 shrink-0 rounded-full bg-primary flex items-center justify-center text-sm font-bold text-primary-foreground">
                  {item.step}
                </div>
                <div>
                  <h3 className="text-sm font-semibold mb-1">{item.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{item.desc}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="container-mobile py-12 pb-16 text-center">
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="p-6 space-y-4">
            <h2 className="text-lg font-bold">Ready to Prove Your Cricket Knowledge?</h2>
            <p className="text-sm text-muted-foreground">
              Join the community and start competing today. It&apos;s free!
            </p>
            <Link href="/signup">
              <Button size="lg">Get Started Now</Button>
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
