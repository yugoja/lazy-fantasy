'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '@/lib/auth';
import { getMatchDetail, MatchDetail } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Trophy, Target, Star, Clock } from 'lucide-react';
import { getFlagUrl } from '@/lib/utils';

export default function MatchDetailPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const matchId = Number(params.id);

  const [match, setMatch] = useState<MatchDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (matchId && isAuthenticated) {
      loadMatch();
    }
  }, [matchId, isAuthenticated]);

  const loadMatch = async () => {
    try {
      const data = await getMatchDetail(matchId);
      setMatch(data);
    } catch {
      setError('Failed to load match');
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (!match) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Card className="p-6 text-center space-y-3">
          <p className="text-sm text-destructive">{error || 'Match not found'}</p>
          <Link href="/predictions">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Matches
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const isCompleted = match.status === 'COMPLETED';
  const isScheduled = match.status === 'SCHEDULED';
  const flag1 = getFlagUrl(match.team_1.short_name);
  const flag2 = getFlagUrl(match.team_2.short_name);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <div className="container-mobile py-6 space-y-5 pb-24">
      {/* Back navigation */}
      <Link
        href="/predictions"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </Link>

      {/* Match Header Card */}
      <Card className="border-border bg-card overflow-hidden">
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-4">
            <Badge
              variant={isCompleted ? 'secondary' : 'default'}
              className="text-[10px] font-semibold uppercase"
            >
              {match.status}
            </Badge>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{formatTime(match.start_time)}</span>
            </div>
          </div>

          {/* Teams */}
          <div className="flex items-center justify-between gap-4">
            {/* Team 1 */}
            <div className="flex flex-col items-center gap-2 flex-1">
              {flag1 && (
                <Image
                  src={flag1}
                  alt={`${match.team_1.name} flag`}
                  width={56}
                  height={40}
                  className="h-10 w-14 object-cover rounded"
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              )}
              <span className="font-bold text-lg">{match.team_1.short_name}</span>
              <span className="text-xs text-muted-foreground text-center">{match.team_1.name}</span>
              {isCompleted && match.winner?.id === match.team_1.id && (
                <Badge className="text-[10px]">Winner</Badge>
              )}
            </div>

            <span className="text-lg font-bold text-muted-foreground">vs</span>

            {/* Team 2 */}
            <div className="flex flex-col items-center gap-2 flex-1">
              {flag2 && (
                <Image
                  src={flag2}
                  alt={`${match.team_2.name} flag`}
                  width={56}
                  height={40}
                  className="h-10 w-14 object-cover rounded"
                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                />
              )}
              <span className="font-bold text-lg">{match.team_2.short_name}</span>
              <span className="text-xs text-muted-foreground text-center">{match.team_2.name}</span>
              {isCompleted && match.winner?.id === match.team_2.id && (
                <Badge className="text-[10px]">Winner</Badge>
              )}
            </div>
          </div>

          <p className="text-xs text-muted-foreground text-center mt-4">
            {formatDate(match.start_time)}
          </p>
        </CardContent>
      </Card>

      {/* Results Section - only for completed */}
      {isCompleted && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Match Results</h2>

          {/* Winner */}
          {match.winner && (
            <Card className="border-primary/20 bg-primary/5">
              <CardContent className="flex items-center gap-3 p-4">
                <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center">
                  <Trophy className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="text-[10px] text-muted-foreground">Winner</p>
                  <p className="text-sm font-semibold">{match.winner.name}</p>
                </div>
                <Badge variant="outline" className="text-[10px]">+10 pts</Badge>
              </CardContent>
            </Card>
          )}

          {/* Most Runs */}
          {match.most_runs_player && (
            <Card className="border-border bg-card">
              <CardContent className="flex items-center gap-3 p-4">
                <div className="h-9 w-9 rounded-full bg-blue-500/10 flex items-center justify-center">
                  <Target className="h-4 w-4 text-blue-400" />
                </div>
                <div className="flex-1">
                  <p className="text-[10px] text-muted-foreground">Most Runs</p>
                  <p className="text-sm font-semibold">{match.most_runs_player.name}</p>
                </div>
                <Badge variant="outline" className="text-[10px]">+20 pts</Badge>
              </CardContent>
            </Card>
          )}

          {/* Most Wickets */}
          {match.most_wickets_player && (
            <Card className="border-border bg-card">
              <CardContent className="flex items-center gap-3 p-4">
                <div className="h-9 w-9 rounded-full bg-green-500/10 flex items-center justify-center">
                  <Target className="h-4 w-4 text-green-400" />
                </div>
                <div className="flex-1">
                  <p className="text-[10px] text-muted-foreground">Most Wickets</p>
                  <p className="text-sm font-semibold">{match.most_wickets_player.name}</p>
                </div>
                <Badge variant="outline" className="text-[10px]">+20 pts</Badge>
              </CardContent>
            </Card>
          )}

          {/* Player of the Match */}
          {match.pom_player && (
            <Card className="border-border bg-card">
              <CardContent className="flex items-center gap-3 p-4">
                <div className="h-9 w-9 rounded-full bg-yellow-500/10 flex items-center justify-center">
                  <Star className="h-4 w-4 text-yellow-400" />
                </div>
                <div className="flex-1">
                  <p className="text-[10px] text-muted-foreground">Player of the Match</p>
                  <p className="text-sm font-semibold">{match.pom_player.name}</p>
                </div>
                <Badge variant="outline" className="text-[10px]">+50 pts</Badge>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Action for scheduled matches */}
      {isScheduled && (
        <Link href={`/matches/${matchId}/predict`}>
          <Button className="w-full" size="lg">
            Make Prediction
          </Button>
        </Link>
      )}
    </div>
  );
}
