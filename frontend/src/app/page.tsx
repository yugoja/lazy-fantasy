'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Trophy, Users, Target, BarChart3, CheckCircle2, Swords } from 'lucide-react';

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

      {/* Hero */}
      <section className="container-mobile pt-14 pb-10 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-xs text-primary font-medium mb-6">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
          </span>
          IPL 2026 · Live Now
        </div>

        <h1 className="text-3xl font-bold tracking-tight mb-3 leading-tight">
          Your mates think they
          <br />
          <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            know cricket.
          </span>
        </h1>

        <p className="text-base text-muted-foreground max-w-sm mx-auto mb-2 leading-relaxed">
          Prove them wrong.
        </p>
        <p className="text-sm text-muted-foreground max-w-sm mx-auto mb-8 leading-relaxed">
          Predict every IPL match, play in a private league with your crew, and
          settle the group chat debate — who actually knows cricket?
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/signup">
            <Button size="lg" className="w-full sm:w-auto font-semibold">
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

      {/* What You Predict — mock prediction card */}
      <section className="container-mobile py-10">
        <div className="text-center mb-6">
          <h2 className="text-xl font-bold mb-1">What you predict</h2>
          <p className="text-sm text-muted-foreground">Six picks per match. Up to 140 pts.</p>
        </div>

        <Card className="border-border bg-card overflow-hidden">
          {/* Match header */}
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">Mumbai Indians</span>
            </div>
            <span className="text-xs text-muted-foreground font-medium">vs</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">Chennai Super Kings</span>
            </div>
          </div>

          <CardContent className="p-4 space-y-3">
            {[
              { label: 'Match Winner', example: 'Mumbai Indians', pts: 10, done: true },
              { label: 'Top Batter · MI', example: 'Rohit Sharma', pts: 20, done: true },
              { label: 'Top Batter · CSK', example: 'Ruturaj Gaikwad', pts: 20, done: true },
              { label: 'Top Bowler · MI', example: 'Jasprit Bumrah', pts: 20, done: false },
              { label: 'Top Bowler · CSK', example: 'Deepak Chahar', pts: 20, done: false },
              { label: 'Player of the Match', example: 'MS Dhoni', pts: 50, done: false },
            ].map((row) => (
              <div key={row.label} className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <CheckCircle2
                    className={`h-4 w-4 shrink-0 ${row.done ? 'text-primary' : 'text-muted-foreground/30'}`}
                  />
                  <div className="min-w-0">
                    <p className="text-xs text-muted-foreground">{row.label}</p>
                    <p className={`text-sm font-medium truncate ${row.done ? 'text-foreground' : 'text-muted-foreground/50'}`}>
                      {row.done ? row.example : '—'}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-primary font-semibold shrink-0">+{row.pts} pts</span>
              </div>
            ))}

            <div className="pt-2 border-t border-border flex items-center justify-between">
              <span className="text-xs text-muted-foreground">Max this match</span>
              <span className="text-sm font-bold text-primary">140 pts</span>
            </div>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-muted-foreground mt-3">
          Predictions lock when the match starts. No cheeky last-minute changes. 😏
        </p>
      </section>

      {/* How It Works */}
      <section className="container-mobile py-10">
        <div className="text-center mb-6">
          <h2 className="text-xl font-bold mb-1">How It Works</h2>
          <p className="text-sm text-muted-foreground">Ready in under 2 minutes</p>
        </div>

        <div className="space-y-3">
          {[
            {
              step: '1',
              icon: Users,
              title: 'Create a league & invite your crew',
              desc: 'Sign up, name your league, and share a code. Your mates join — no app installs needed.',
            },
            {
              step: '2',
              icon: Target,
              title: 'Predict before every match',
              desc: 'Pick the winner, top batter and top bowler from each team, and the player of the match. Six picks. One shot at glory.',
            },
            {
              step: '3',
              icon: BarChart3,
              title: 'Watch the leaderboard heat up',
              desc: 'Points update after every match. Trash talk freely. The real World Cup is in your group chat.',
            },
          ].map((item) => (
            <Card key={item.step} className="border-border bg-card">
              <CardContent className="flex items-start gap-4 p-4">
                <div className="h-10 w-10 shrink-0 rounded-lg bg-primary/10 flex items-center justify-center">
                  <item.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold mb-0.5">{item.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{item.desc}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* More sports coming */}
      <section className="container-mobile py-6">
        <Card className="border-border bg-card">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground text-center mb-3 font-medium uppercase tracking-wider">More sports coming soon</p>
            <div className="flex items-center justify-center gap-6">
              <div className="flex items-center gap-2 opacity-50">
                <span className="text-2xl">🏎️</span>
                <div>
                  <p className="text-sm font-semibold">Formula 1</p>
                  <p className="text-xs text-muted-foreground">2026 Season</p>
                </div>
              </div>
              <div className="h-8 w-px bg-border" />
              <div className="flex items-center gap-2 opacity-50">
                <span className="text-2xl">⚽</span>
                <div>
                  <p className="text-sm font-semibold">Football</p>
                  <p className="text-xs text-muted-foreground">World Cup 2026</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Bottom CTA */}
      <section className="container-mobile py-10 pb-16 text-center">
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="p-6 space-y-3">
            <Swords className="h-8 w-8 text-primary mx-auto" />
            <h2 className="text-lg font-bold">IPL 2026 is live.</h2>
            <p className="text-sm text-muted-foreground">
              Your group chat needs settling. Create a league, share the code, and let the
              banter begin.
            </p>
            <Link href="/signup">
              <Button size="lg" className="font-semibold">Challenge Your Mates</Button>
            </Link>
            <p className="text-xs text-muted-foreground">Free to play. Always.</p>
          </CardContent>
        </Card>
      </section>

    </div>
  );
}
