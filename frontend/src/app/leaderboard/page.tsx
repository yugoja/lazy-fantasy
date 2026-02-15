'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMyLeagues, getLeaderboard } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Trophy } from 'lucide-react';
import { cn } from '@/lib/utils';

interface League {
  id: number;
  name: string;
  invite_code: string;
  owner_id: number;
}

interface LeaderboardEntry {
  user_id: number;
  username: string;
  total_points: number;
  rank: number;
}

export default function LeaderboardPage() {
  const { isAuthenticated, username, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [selectedLeagueId, setSelectedLeagueId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [boardLoading, setBoardLoading] = useState(false);

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
      const data = await getMyLeagues();
      setLeagues(data);
      if (data.length > 0) {
        const firstId = String(data[0].id);
        setSelectedLeagueId(firstId);
        await loadBoard(data[0].id);
      }
    } catch {
      // handled by empty state
    } finally {
      setIsLoading(false);
    }
  };

  const loadBoard = async (leagueId: number) => {
    setBoardLoading(true);
    try {
      const data = await getLeaderboard(leagueId);
      setEntries(data.entries);
    } catch {
      setEntries([]);
    } finally {
      setBoardLoading(false);
    }
  };

  const handleLeagueChange = (val: string) => {
    setSelectedLeagueId(val);
    loadBoard(Number(val));
  };

  const currentUserEntry = entries.find(e => e.username === username);

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-32 w-full" />
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    );
  }

  if (leagues.length === 0) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <h1 className="text-2xl font-bold">Leaderboard</h1>
        <Card className="p-8 text-center space-y-3">
          <Trophy className="h-10 w-10 text-muted-foreground mx-auto" />
          <p className="text-sm text-muted-foreground">Join a league to see leaderboards</p>
          <Link href="/leagues">
            <Button size="sm">Browse Leagues</Button>
          </Link>
        </Card>
      </div>
    );
  }

  const topThree = entries.slice(0, 3);
  const [first, second, third] = [topThree[0], topThree[1], topThree[2]];

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Leaderboard</h1>
        <Select value={selectedLeagueId} onValueChange={handleLeagueChange}>
          <SelectTrigger className="w-full mt-3">
            <SelectValue placeholder="Select a league" />
          </SelectTrigger>
          <SelectContent>
            {leagues.map((league) => (
              <SelectItem key={league.id} value={String(league.id)}>
                {league.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {boardLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-32 w-full" />
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <Card className="p-8 text-center">
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
                      {second.username.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-xs truncate w-full">{second.username}</div>
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
                      {first.username.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-sm truncate w-full">{first.username}</div>
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
                      {third.username.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-xs truncate w-full">{third.username}</div>
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
