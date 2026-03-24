'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getLeagueMatchPredictions, getMatchDetail, getMyLeagues, FriendPrediction } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Trophy, Target, Star, Check, X, ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MatchInfo {
  id: number;
  team_1: { id: number; name: string; short_name: string };
  team_2: { id: number; name: string; short_name: string };
  start_time: string;
  status: string;
}

interface League {
  id: number;
  name: string;
  invite_code: string;
  owner_id: number;
}

const CATEGORIES = [
  { key: 'winner', label: 'Winner', icon: Trophy, pts: 10, color: 'text-primary' },
  { key: 'runs_t1', label: 'Runs (T1)', icon: Target, pts: 20, color: 'text-blue-400' },
  { key: 'runs_t2', label: 'Runs (T2)', icon: Target, pts: 20, color: 'text-blue-300' },
  { key: 'wkts_t1', label: 'Wkts (T1)', icon: Target, pts: 20, color: 'text-green-400' },
  { key: 'wkts_t2', label: 'Wkts (T2)', icon: Target, pts: 20, color: 'text-green-300' },
  { key: 'pom', label: 'POM', icon: Star, pts: 50, color: 'text-yellow-400' },
] as const;

function getCategoryData(pred: FriendPrediction, match: MatchInfo) {
  return [
    {
      label: `Winner`,
      icon: Trophy,
      pts: 10,
      color: 'text-primary',
      predicted: pred.predicted_winner.short_name,
      actual: pred.actual_winner?.short_name ?? null,
    },
    {
      label: `Runs (${match.team_1.short_name})`,
      icon: Target,
      pts: 20,
      color: 'text-blue-400',
      predicted: pred.predicted_most_runs_team1_player.name,
      actual: pred.actual_most_runs_team1_player?.name ?? null,
    },
    {
      label: `Runs (${match.team_2.short_name})`,
      icon: Target,
      pts: 20,
      color: 'text-blue-300',
      predicted: pred.predicted_most_runs_team2_player.name,
      actual: pred.actual_most_runs_team2_player?.name ?? null,
    },
    {
      label: `Wkts (${match.team_1.short_name})`,
      icon: Target,
      pts: 20,
      color: 'text-green-400',
      predicted: pred.predicted_most_wickets_team1_player.name,
      actual: pred.actual_most_wickets_team1_player?.name ?? null,
    },
    {
      label: `Wkts (${match.team_2.short_name})`,
      icon: Target,
      pts: 20,
      color: 'text-green-300',
      predicted: pred.predicted_most_wickets_team2_player.name,
      actual: pred.actual_most_wickets_team2_player?.name ?? null,
    },
    {
      label: 'POM',
      icon: Star,
      pts: 50,
      color: 'text-yellow-400',
      predicted: pred.predicted_pom_player.name,
      actual: pred.actual_pom_player?.name ?? null,
    },
  ];
}

function PredictionCard({ pred, match }: { pred: FriendPrediction; match: MatchInfo }) {
  const cats = getCategoryData(pred, match);
  const initials = pred.username.substring(0, 2).toUpperCase();

  return (
    <Card className={cn('border-border', pred.is_me && 'border-primary/40 bg-primary/5')}>
      <CardContent className="p-4 space-y-3">
        {/* User row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
              {initials}
            </div>
            <span className="font-semibold text-sm">{pred.username}</span>
            {pred.is_me && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">You</Badge>
            )}
          </div>
          {pred.is_processed ? (
            <Badge variant={pred.points_earned > 0 ? 'default' : 'secondary'} className="text-[10px]">
              +{pred.points_earned} pts
            </Badge>
          ) : (
            <Badge variant="outline" className="text-[10px]">Pending</Badge>
          )}
        </div>

        {/* Picks */}
        <div className="space-y-1.5">
          {cats.map((cat) => {
            const isCorrect = pred.is_processed && cat.actual !== null && cat.predicted === cat.actual;
            const isWrong = pred.is_processed && cat.actual !== null && cat.predicted !== cat.actual;
            const CatIcon = cat.icon;
            return (
              <div key={cat.label} className="flex items-center gap-2 text-xs">
                <CatIcon className={cn('h-3 w-3 shrink-0', cat.color)} />
                <span className="text-muted-foreground w-[4.5rem] shrink-0 text-[11px]">{cat.label}</span>
                <span className={cn(
                  'flex-1 truncate font-medium text-[11px]',
                  isCorrect && 'text-green-400',
                  isWrong && 'text-muted-foreground line-through',
                )}>
                  {cat.predicted}
                </span>
                {isCorrect && (
                  <div className="flex items-center gap-0.5 shrink-0">
                    <Check className="h-3 w-3 text-green-400" />
                    <span className="text-[10px] font-semibold text-green-400">+{cat.pts}</span>
                  </div>
                )}
                {isWrong && (
                  <div className="flex items-center gap-0.5 shrink-0">
                    <X className="h-3 w-3 text-red-400" />
                    <span className="text-[10px] text-muted-foreground truncate max-w-[4.5rem]">{cat.actual}</span>
                  </div>
                )}
                {!pred.is_processed && (
                  <span className="text-[10px] text-muted-foreground shrink-0">+{cat.pts}</span>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default function LeagueMatchPredictionsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const leagueId = Number(params.leagueId);
  const matchId = Number(params.matchId);

  const [predictions, setPredictions] = useState<FriendPrediction[]>([]);
  const [match, setMatch] = useState<MatchInfo | null>(null);
  const [leagues, setLeagues] = useState<League[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    loadData();
  }, [isAuthenticated, leagueId, matchId]);

  const loadData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const [predsData, matchData, leaguesData] = await Promise.all([
        getLeagueMatchPredictions(leagueId, matchId),
        getMatchDetail(matchId),
        getMyLeagues(),
      ]);
      setPredictions(predsData);
      setMatch(matchData);
      setLeagues(leaguesData);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load predictions');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleLeagueChange = (val: string) => {
    router.push(`/leagues/${val}/match/${matchId}`);
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-full" />
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-40" />)}
      </div>
    );
  }

  if (error) {
    return (
      <div className="container-mobile py-6 space-y-4">
        <Link href="/predictions" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary">
          <ChevronLeft className="h-4 w-4" /> Back
        </Link>
        <Card className="p-6 text-center border-destructive/50 bg-destructive/10">
          <p className="text-sm text-destructive">{error}</p>
        </Card>
      </div>
    );
  }

  const currentLeague = leagues.find(l => l.id === leagueId);

  return (
    <div className="container-mobile py-6 space-y-4 pb-24">
      {/* Back */}
      <Link href="/predictions" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary">
        <ChevronLeft className="h-4 w-4" /> Back to Predictions
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold">
          {match ? `${match.team_1.short_name} vs ${match.team_2.short_name}` : 'Friends\' Picks'}
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {match ? new Date(match.start_time).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) : ''}
        </p>
      </div>

      {/* League selector */}
      {leagues.length > 1 && (
        <Select value={String(leagueId)} onValueChange={handleLeagueChange}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select league" />
          </SelectTrigger>
          <SelectContent>
            {leagues.map(l => (
              <SelectItem key={l.id} value={String(l.id)}>{l.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      {leagues.length === 1 && currentLeague && (
        <p className="text-xs text-muted-foreground">{currentLeague.name}</p>
      )}

      {/* Count */}
      <Badge variant="secondary" className="text-xs">
        {predictions.length} prediction{predictions.length !== 1 ? 's' : ''}
      </Badge>

      {/* Cards */}
      {predictions.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-muted-foreground">No one in this league has predicted this match yet.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {predictions.map((pred, i) => (
            <PredictionCard key={i} pred={pred} match={match!} />
          ))}
        </div>
      )}
    </div>
  );
}
