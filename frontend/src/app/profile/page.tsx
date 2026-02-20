'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMyLeagues, getMyPredictionsDetailed, PredictionDetail } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Trophy,
  Target,
  Flame,
  ChevronRight,
  LogOut,
  Bell,
  Shield,
  CircleHelp,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface League {
  id: number;
  name: string;
  invite_code: string;
  owner_id: number;
}

export default function ProfilePage() {
  const { isAuthenticated, isLoading: authLoading, username, logout } = useAuth();
  const router = useRouter();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [predictions, setPredictions] = useState<PredictionDetail[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadLeagues();
    }
  }, [isAuthenticated]);

  const loadLeagues = async () => {
    try {
      const [leaguesData, predictionsData] = await Promise.allSettled([
        getMyLeagues(),
        getMyPredictionsDetailed(),
      ]);
      if (leaguesData.status === 'fulfilled') setLeagues(leaguesData.value);
      if (predictionsData.status === 'fulfilled') setPredictions(predictionsData.value);
    } catch {
      // silently fail - non-critical
    } finally {
      setIsLoading(false);
    }
  };

  const processed = predictions.filter(p => p.is_processed);
  const totalPoints = processed.reduce((sum, p) => sum + p.points_earned, 0);
  const correctWins = processed.filter(p => p.actual_winner && p.predicted_winner.id === p.actual_winner.id).length;
  const accuracy = processed.length > 0 ? Math.round((correctWins / processed.length) * 100) : 0;

  // Streak: consecutive correct winner picks from most recent processed match
  const sortedProcessed = [...processed].sort(
    (a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
  );
  let streak = 0;
  for (const p of sortedProcessed) {
    if (p.actual_winner && p.predicted_winner.id === p.actual_winner.id) {
      streak++;
    } else {
      break;
    }
  }

  const initials = username
    ? username.substring(0, 2).toUpperCase()
    : '??';

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-5">
        <div className="flex flex-col items-center space-y-3">
          <Skeleton className="h-20 w-20 rounded-full" />
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-32" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  return (
    <div className="container-mobile py-6 space-y-5 pb-24">
      {/* Profile Avatar */}
      <div className="flex flex-col items-center">
        <div className="relative">
          <Avatar className="h-20 w-20 border-2 border-primary">
            <AvatarFallback className="bg-primary/15 text-2xl font-bold text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full bg-accent">
            <Trophy className="h-3.5 w-3.5 text-accent-foreground" />
          </div>
        </div>
        <h1 className="mt-3 text-lg font-bold text-foreground">{username}</h1>
        <p className="text-xs text-muted-foreground">@{username}</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Points', value: String(totalPoints), icon: Trophy, color: 'text-primary' },
          { label: 'Accuracy', value: processed.length > 0 ? `${accuracy}%` : '0%', icon: Target, color: 'text-accent' },
          { label: 'Streak', value: String(streak), icon: Flame, color: 'text-orange-400' },
        ].map((stat) => (
          <Card key={stat.label} className="border-border bg-card">
            <CardContent className="flex flex-col items-center gap-1 p-3">
              <stat.icon className={cn('h-4 w-4', stat.color)} />
              <span className="text-lg font-bold text-foreground">{stat.value}</span>
              <span className="text-[10px] text-muted-foreground">{stat.label}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Personal Info */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-foreground">Personal Info</h2>
        <Card className="border-border bg-card">
          <CardContent className="flex flex-col gap-4 p-4">
            <div className="flex flex-col gap-1.5">
              <Label className="text-[11px] text-muted-foreground">Username</Label>
              <p className="text-sm font-medium text-foreground">@{username}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* My Leagues */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">My Leagues</h2>
          <Badge variant="secondary" className="text-[10px]">
            {leagues.length}
          </Badge>
        </div>
        <Card className="border-border bg-card">
          {leagues.length === 0 ? (
            <CardContent className="p-4 text-center">
              <p className="text-sm text-muted-foreground">No leagues joined yet</p>
              <Link href="/leagues" className="mt-2 inline-block">
                <Button variant="outline" size="sm" className="text-xs mt-2">
                  Browse Leagues
                </Button>
              </Link>
            </CardContent>
          ) : (
            <CardContent className="divide-y divide-border p-0">
              {leagues.map((league) => (
                <Link
                  key={league.id}
                  href={`/leaderboard?league=${league.id}`}
                  className="flex items-center justify-between px-4 py-3 active:bg-secondary/50"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                      <Users className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <p className="text-sm font-medium text-foreground">{league.name}</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              ))}
            </CardContent>
          )}
        </Card>
      </div>

      {/* Settings Menu */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-foreground">Settings</h2>
        <Card className="border-border bg-card">
          <CardContent className="divide-y divide-border p-0">
            {[
              { icon: Bell, label: 'Notifications', desc: 'Match reminders & results' },
              { icon: Shield, label: 'Privacy', desc: 'Profile visibility & data' },
              { icon: CircleHelp, label: 'Help & Support', desc: 'FAQs and contact us' },
            ].map((item) => (
              <button
                key={item.label}
                className="flex w-full items-center justify-between px-4 py-3 active:bg-secondary/50"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary">
                    <item.icon className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium text-foreground">{item.label}</p>
                    <p className="text-[10px] text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Sign Out */}
      <Button
        variant="outline"
        className="w-full border-destructive/30 bg-destructive/5 text-destructive active:bg-destructive/10"
        onClick={logout}
      >
        <LogOut className="mr-2 h-4 w-4" />
        Sign Out
      </Button>
    </div>
  );
}
