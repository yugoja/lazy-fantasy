'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Trophy, TrendingUp, TrendingDown, Minus, Flame } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LeaderboardPlayer {
  rank: number;
  username: string;
  points: number;
  streak: number;
  trend: 'up' | 'down' | 'same';
}

export default function LeaderboardPage() {
  const { isAuthenticated, username, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [selectedLeague, setSelectedLeague] = useState('global');

  // Mock data - replace with API call
  const mockPlayers: LeaderboardPlayer[] = [
    { rank: 1, username: 'CricketPro', points: 310, streak: 5, trend: 'up' },
    { rank: 2, username: 'FantasyKing', points: 278, streak: 3, trend: 'up' },
    { rank: 3, username: username || 'You', points: 245, streak: 2, trend: 'same' },
    { rank: 4, username: 'MatchMaster', points: 223, streak: 1, trend: 'down' },
    { rank: 5, username: 'Predictor99', points: 198, streak: 4, trend: 'up' },
  ];

  const currentUserRank = mockPlayers.find(p => p.username === username);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    } else {
      setTimeout(() => setIsLoading(false), 500);
    }
  }, [isAuthenticated, authLoading, router]);

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const topThree = mockPlayers.slice(0, 3);
  const [second, first, third] = topThree.length === 3
    ? [topThree[1], topThree[0], topThree[2]]
    : [null, topThree[0], null];

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Leaderboard</h1>
        <Select value={selectedLeague} onValueChange={setSelectedLeague}>
          <SelectTrigger className="w-full mt-3">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="global">Global Rankings</SelectItem>
            <SelectItem value="cricket-fanatics">Cricket Fanatics</SelectItem>
            <SelectItem value="office-squad">Office Squad</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Current User Status */}
      {currentUserRank && (
        <Card className="p-4 bg-primary/5 border-primary/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl font-bold text-primary">#{currentUserRank.rank}</div>
              <div>
                <div className="font-semibold">You</div>
                <div className="text-xs text-muted-foreground">{currentUserRank.points} pts</div>
              </div>
            </div>
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30">
              Top {Math.round((currentUserRank.rank / mockPlayers.length) * 100)}%
            </Badge>
          </div>
        </Card>
      )}

      {/* Top 3 Podium */}
      <div className="grid grid-cols-3 gap-2 items-end mb-6">
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
              <div className="text-sm font-bold text-primary mt-1">{second.points}</div>
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
              <div className="text-lg font-bold text-primary mt-1">{first.points}</div>
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
              <div className="text-sm font-bold text-primary mt-1">{third.points}</div>
              <div className="text-[10px] text-muted-foreground">points</div>
            </div>
          </Card>
        )}
      </div>

      {/* Full Table */}
      <Card className="overflow-hidden">
        <div className="divide-y divide-border">
          {mockPlayers.map((player, index) => {
            const isCurrentUser = player.username === username;
            const TrendIcon = player.trend === 'up' ? TrendingUp : player.trend === 'down' ? TrendingDown : Minus;
            const trendColor = player.trend === 'up' ? 'text-green-500' : player.trend === 'down' ? 'text-red-500' : 'text-muted-foreground';

            return (
              <div
                key={player.username}
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
                  {player.rank}
                </div>

                {/* Avatar & Name */}
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-primary/10 text-primary font-bold text-sm">
                      {player.username.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm truncate">{player.username}</div>
                    {isCurrentUser && (
                      <Badge variant="outline" className="text-[10px] mt-0.5">You</Badge>
                    )}
                  </div>
                </div>

                {/* Points */}
                <div className="text-right">
                  <div className="font-bold text-sm">{player.points}</div>
                  <div className="text-[10px] text-muted-foreground">pts</div>
                </div>

                {/* Streak */}
                {player.streak > 0 && (
                  <div className="flex items-center gap-1">
                    <Flame className="h-4 w-4 text-orange-500" />
                    <span className="text-sm font-semibold">{player.streak}</span>
                  </div>
                )}

                {/* Trend */}
                <TrendIcon className={cn('h-4 w-4', trendColor)} />
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
