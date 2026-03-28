'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getLeaderboard, getMyLeagues } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Trophy, TrendingUp, TrendingDown, Minus, ArrowLeft, Share2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface LeaderboardEntry {
  user_id: number;
  username: string;
  display_name?: string | null;
  total_points: number;
  rank: number;
  rank_delta: number | null;
}

function entryLabel(entry: LeaderboardEntry) {
  return entry.display_name || entry.username;
}

export default function LeagueLeaderboardPage() {
  const { isAuthenticated, username, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const leagueId = Number(params.leagueId);

  const [leagueName, setLeagueName] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated && leagueId) {
      loadBoard();
    }
  }, [isAuthenticated, leagueId]);

  const loadBoard = async () => {
    try {
      const [data, leagues] = await Promise.all([
        getLeaderboard(leagueId),
        getMyLeagues(),
      ]);
      setLeagueName(data.league_name);
      setEntries(data.entries);
      const league = leagues.find((l) => l.id === leagueId);
      if (league) setInviteCode(league.invite_code);
    } catch {
      // empty state
    } finally {
      setIsLoading(false);
    }
  };

  const handleShare = async () => {
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app';
    const joinUrl = `${appUrl}/join/${inviteCode}`;
    const text = `Join my Lazy Fantasy league "${leagueName}"!\n\nTap to join: ${joinUrl}`;
    try {
      if (navigator.share) {
        await navigator.share({ text });
      } else {
        await navigator.clipboard.writeText(text);
        toast({ description: 'Invite link copied to clipboard' });
      }
    } catch {
      // user cancelled
    }
  };

  const currentUserEntry = entries.find(e => e.username === username);

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  const topThree = entries.slice(0, 3);
  const [first, second, third] = [topThree[0], topThree[1], topThree[2]];

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Header */}
      <div>
        <Link href="/leagues">
          <Button variant="ghost" size="sm" className="mb-3 -ml-2 text-muted-foreground">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Leagues
          </Button>
        </Link>
        <div className="flex items-center justify-between gap-3">
          <h1 className="text-2xl font-bold">{leagueName || 'Leaderboard'}</h1>
          {inviteCode && (
            <Button variant="outline" size="sm" onClick={handleShare} className="shrink-0 gap-2">
              <Share2 className="h-4 w-4" />
              Invite
            </Button>
          )}
        </div>
      </div>

      {entries.length === 0 ? (
        <Card className="p-8 text-center space-y-3">
          <Trophy className="h-10 w-10 text-muted-foreground mx-auto" />
          <p className="text-sm text-muted-foreground">No entries yet. Start predicting!</p>
        </Card>
      ) : (
        <>
          {/* Current User Status */}
          {currentUserEntry && (
            <Card className="p-4 bg-primary/5 border-primary/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="text-2xl font-bold text-primary">#{currentUserEntry.rank}</div>
                  <div>
                    <div className="font-semibold">You</div>
                    <div className="text-xs text-muted-foreground">{currentUserEntry.total_points} pts</div>
                  </div>
                </div>
                <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30">
                  Top {Math.max(1, Math.round((currentUserEntry.rank / entries.length) * 100))}%
                </Badge>
              </div>
            </Card>
          )}

          {/* Top 3 Podium */}
          {topThree.length >= 3 && (
            <div className="grid grid-cols-3 gap-2 items-end mb-6">
              {/* 2nd Place */}
              <Card className="p-3 text-center bg-gradient-to-b from-slate-700/10 to-transparent">
                <div className="flex flex-col items-center">
                  <div className="text-3xl mb-2">🥈</div>
                  <Avatar className="h-12 w-12 mb-2 border-2 border-slate-400">
                    <AvatarFallback className="bg-slate-500 text-white font-bold">
                      {entryLabel(second).substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-xs truncate w-full">{entryLabel(second)}</div>
                  <div className="text-sm font-bold text-primary mt-1">{second.total_points}</div>
                  <div className="text-[10px] text-muted-foreground">points</div>
                </div>
              </Card>

              {/* 1st Place */}
              <Card className="p-4 text-center bg-gradient-to-b from-amber-500/10 to-transparent border-amber-500/30">
                <div className="flex flex-col items-center">
                  <Trophy className="h-8 w-8 text-amber-500 mb-2" />
                  <Avatar className="h-16 w-16 mb-2 border-2 border-amber-500">
                    <AvatarFallback className="bg-amber-600 text-white font-bold text-lg">
                      {entryLabel(first).substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-sm truncate w-full">{entryLabel(first)}</div>
                  <div className="text-lg font-bold text-primary mt-1">{first.total_points}</div>
                  <div className="text-[10px] text-muted-foreground">points</div>
                </div>
              </Card>

              {/* 3rd Place */}
              <Card className="p-3 text-center bg-gradient-to-b from-orange-700/10 to-transparent">
                <div className="flex flex-col items-center">
                  <div className="text-3xl mb-2">🥉</div>
                  <Avatar className="h-12 w-12 mb-2 border-2 border-orange-600">
                    <AvatarFallback className="bg-orange-700 text-white font-bold">
                      {entryLabel(third).substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-xs truncate w-full">{entryLabel(third)}</div>
                  <div className="text-sm font-bold text-primary mt-1">{third.total_points}</div>
                  <div className="text-[10px] text-muted-foreground">points</div>
                </div>
              </Card>
            </div>
          )}

          {/* Full Table */}
          <Card className="overflow-hidden">
            <div className="divide-y divide-border">
              {entries.map((entry) => {
                const isCurrentUser = entry.username === username;
                const delta = entry.rank_delta ?? null;
                return (
                  <div
                    key={entry.user_id}
                    className={cn(
                      'p-4 flex items-center gap-4',
                      isCurrentUser && 'bg-primary/5'
                    )}
                  >
                    <div className={cn(
                      'text-lg font-bold w-8 text-center',
                      entry.rank <= 3 ? 'text-primary' : 'text-muted-foreground'
                    )}>
                      {entry.rank}
                    </div>

                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <Avatar className="h-10 w-10">
                        <AvatarFallback className="bg-primary/10 text-primary font-bold text-sm">
                          {entryLabel(entry).substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-sm truncate">{entryLabel(entry)}</div>
                        {isCurrentUser && (
                          <Badge variant="outline" className="text-[10px] mt-0.5">You</Badge>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {delta !== null && delta !== 0 && (
                        <div className={cn(
                          'flex items-center gap-0.5 text-[10px] font-medium',
                          delta > 0 ? 'text-green-500' : 'text-red-500'
                        )}>
                          {delta > 0
                            ? <TrendingUp className="h-3 w-3" />
                            : <TrendingDown className="h-3 w-3" />}
                          {Math.abs(delta)}
                        </div>
                      )}
                      {delta === 0 && (
                        <Minus className="h-3 w-3 text-muted-foreground/50" />
                      )}
                      <div className="text-right">
                        <div className="font-bold text-sm">{entry.total_points}</div>
                        <div className="text-[10px] text-muted-foreground">pts</div>
                      </div>
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
