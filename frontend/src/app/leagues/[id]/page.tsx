'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getLeaderboard, ApiError } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Share2, Trophy, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LeaderboardEntry {
  user_id: number;
  username: string;
  total_points: number;
  rank: number;
}

interface Leaderboard {
  league_id: number;
  league_name: string;
  entries: LeaderboardEntry[];
}

export default function LeagueDetailPage() {
  const { isAuthenticated, isLoading: authLoading, username } = useAuth();
  const router = useRouter();
  const params = useParams();
  const leagueId = Number(params.id);

  const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated && leagueId) {
      loadLeaderboard();
    }
  }, [isAuthenticated, leagueId]);

  const loadLeaderboard = async () => {
    try {
      const data = await getLeaderboard(leagueId);
      setLeaderboard(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Failed to load leaderboard');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(`Join my fantasy cricket league!`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-6 w-24" />
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-9 w-28" />
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-36" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Card className="p-6 text-center space-y-3">
          <p className="text-sm text-destructive">{error}</p>
          <Link href="/leagues">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Leagues
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const entries = leaderboard?.entries || [];
  const topThree = entries.slice(0, 3);
  const [second, first, third] = topThree.length === 3
    ? [topThree[1], topThree[0], topThree[2]]
    : [null, topThree[0] || null, null];

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Back navigation */}
      <Link
        href="/leagues"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Leagues
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{leaderboard?.league_name}</h1>
        <Button variant="outline" size="sm" onClick={handleShare}>
          {copied ? (
            <>
              <CheckCircle2 className="h-4 w-4 mr-1.5 text-primary" />
              Copied!
            </>
          ) : (
            <>
              <Share2 className="h-4 w-4 mr-1.5" />
              Share Invite
            </>
          )}
        </Button>
      </div>

      {entries.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-muted-foreground">No members yet. Share the invite code to get started!</p>
        </Card>
      ) : (
        <>
          {/* Top 3 Podium */}
          {topThree.length >= 3 && (
            <div className="grid grid-cols-3 gap-2 items-end">
              {/* 2nd Place */}
              {second && (
                <Card className="p-3 text-center bg-gradient-to-b from-slate-700/10 to-transparent">
                  <div className="flex flex-col items-center">
                    <div className="text-3xl mb-2">🥈</div>
                    <Avatar className="h-12 w-12 mb-2 border-2 border-slate-400">
                      <AvatarFallback className="bg-slate-500 text-white font-bold">
                        {second.username.substring(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="font-bold text-xs truncate w-full">{second.username}</div>
                    <div className="text-sm font-bold text-primary mt-1">{second.total_points}</div>
                    <div className="text-[10px] text-muted-foreground">points</div>
                  </div>
                </Card>
              )}

              {/* 1st Place */}
              {first && (
                <Card className="p-4 text-center bg-gradient-to-b from-amber-500/10 to-transparent border-amber-500/30">
                  <div className="flex flex-col items-center">
                    <Trophy className="h-8 w-8 text-amber-500 mb-2" />
                    <Avatar className="h-16 w-16 mb-2 border-2 border-amber-500">
                      <AvatarFallback className="bg-amber-600 text-white font-bold text-lg">
                        {first.username.substring(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="font-bold text-sm truncate w-full">{first.username}</div>
                    <div className="text-lg font-bold text-primary mt-1">{first.total_points}</div>
                    <div className="text-[10px] text-muted-foreground">points</div>
                  </div>
                </Card>
              )}

              {/* 3rd Place */}
              {third && (
                <Card className="p-3 text-center bg-gradient-to-b from-orange-700/10 to-transparent">
                  <div className="flex flex-col items-center">
                    <div className="text-3xl mb-2">🥉</div>
                    <Avatar className="h-12 w-12 mb-2 border-2 border-orange-600">
                      <AvatarFallback className="bg-orange-700 text-white font-bold">
                        {third.username.substring(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="font-bold text-xs truncate w-full">{third.username}</div>
                    <div className="text-sm font-bold text-primary mt-1">{third.total_points}</div>
                    <div className="text-[10px] text-muted-foreground">points</div>
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* Full Table */}
          <Card className="overflow-hidden">
            <div className="divide-y divide-border">
              {entries.map((entry, index) => {
                const isCurrentUser = entry.username === username;
                return (
                  <div
                    key={entry.user_id}
                    className={cn(
                      'p-4 flex items-center gap-4',
                      isCurrentUser && 'bg-primary/5'
                    )}
                  >
                    {/* Rank */}
                    <div className={cn(
                      'text-lg font-bold w-8 text-center',
                      index < 3 ? 'text-primary' : 'text-muted-foreground'
                    )}>
                      {entry.rank}
                    </div>

                    {/* Avatar & Name */}
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Avatar className="h-10 w-10">
                        <AvatarFallback className="bg-primary/10 text-primary font-bold text-sm">
                          {entry.username.substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm truncate">{entry.username}</div>
                        {isCurrentUser && (
                          <Badge variant="outline" className="text-[10px] mt-0.5">You</Badge>
                        )}
                      </div>
                    </div>

                    {/* Points */}
                    <div className="text-right">
                      <div className="font-bold text-sm">{entry.total_points}</div>
                      <div className="text-[10px] text-muted-foreground">pts</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
