'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Trophy, Users, Target, BarChart3 } from 'lucide-react';

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
          <span>ICC T20 World Cup 2026</span>
        </div>

        <h1 className="text-3xl font-bold tracking-tight mb-3">
          Your Fantasy Cricket
          <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent"> League Awaits</span>
        </h1>

        <p className="text-sm text-muted-foreground max-w-md mx-auto mb-8 leading-relaxed">
          Predict match outcomes, compete with friends in private leagues,
          and climb the leaderboard. Free to play.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
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
      </section>

      {/* How It Works — 3 Steps */}
      <section className="container-mobile py-12">
        <div className="text-center mb-8">
          <h2 className="text-xl font-bold mb-2">How It Works</h2>
          <p className="text-sm text-muted-foreground">
            Three steps to get in the game
          </p>
        </div>

        <div className="space-y-4">
          {[
            {
              step: '1',
              icon: Users,
              title: 'Create a League',
              desc: 'Sign up, create a private league, and share the invite code with your friends.',
            },
            {
              step: '2',
              icon: Target,
              title: 'Predict Every Match',
              desc: 'Before each T20 World Cup match, predict the winner, top batsman, top bowler, and player of the match.',
            },
            {
              step: '3',
              icon: BarChart3,
              title: 'Climb the Leaderboard',
              desc: 'Earn points for correct predictions. Track your rank against friends and see who knows cricket best.',
            },
          ].map((item) => (
            <Card key={item.step} className="border-border bg-card">
              <CardContent className="flex items-start gap-4 p-4">
                <div className="h-10 w-10 shrink-0 rounded-lg bg-primary/10 flex items-center justify-center">
                  <item.icon className="h-5 w-5 text-primary" />
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
              The T20 World Cup is on. Join your friends and start predicting.
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
