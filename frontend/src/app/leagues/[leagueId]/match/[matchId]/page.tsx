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

function getCategoryData(pred: FriendPrediction, match: MatchInfo) {
  return [
    {
      label: 'Winner',
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

function computeAgreement(pred: FriendPrediction, myPred: FriendPrediction): number {
  let count = 0;
  if (pred.predicted_winner.short_name === myPred.predicted_winner.short_name) count++;
  if (pred.predicted_most_runs_team1_player.name === myPred.predicted_most_runs_team1_player.name) count++;
  if (pred.predicted_most_runs_team2_player.name === myPred.predicted_most_runs_team2_player.name) count++;
  if (pred.predicted_most_wickets_team1_player.name === myPred.predicted_most_wickets_team1_player.name) count++;
  if (pred.predicted_most_wickets_team2_player.name === myPred.predicted_most_wickets_team2_player.name) count++;
  if (pred.predicted_pom_player.name === myPred.predicted_pom_player.name) count++;
  return count;
}

function isSamePick(cat: ReturnType<typeof getCategoryData>[0], myPred: FriendPrediction, match: MatchInfo, catIndex: number): boolean {
  const myCats = getCategoryData(myPred, match);
  return cat.predicted === myCats[catIndex].predicted;
}

function PredictionCard({
  pred,
  match,
  myPred,
}: {
  pred: FriendPrediction;
  match: MatchInfo;
  myPred: FriendPrediction | null;
}) {
  const cats = getCategoryData(pred, match);
  const initials = pred.username.substring(0, 2).toUpperCase();

  const agreement = !pred.is_me && myPred ? computeAgreement(pred, myPred) : null;
  const agreementColor =
    agreement === null ? '' :
    agreement >= 5 ? 'text-green-400' :
    agreement >= 3 ? 'text-yellow-400' :
    'text-muted-foreground';

  const myPoints = myPred?.points_earned ?? null;
  const h2hDelta = pred.is_processed && !pred.is_me && myPoints !== null
    ? pred.points_earned - myPoints
    : null;

  return (
    <Card className={cn('border-border', pred.is_me && 'border-primary/40 bg-primary/5')}>
      <CardContent className="p-4 space-y-3">
        {/* User row */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0">
              {initials}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-semibold text-sm">{pred.username}</span>
                {pred.is_me && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0">You</Badge>
                )}
              </div>
              {agreement !== null && (
                <p className={cn('text-[10px] mt-0.5', agreementColor)}>
                  Agrees on {agreement}/6 with you
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-0.5">
            {pred.is_processed ? (
              <Badge variant={pred.points_earned > 0 ? 'default' : 'secondary'} className="text-[10px]">
                +{pred.points_earned} pts
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px]">Pending</Badge>
            )}
            {h2hDelta !== null && h2hDelta !== 0 && (
              <span className={cn('text-[10px] font-medium', h2hDelta > 0 ? 'text-red-400' : 'text-green-400')}>
                {h2hDelta > 0 ? `+${h2hDelta} on you` : `You lead by ${Math.abs(h2hDelta)}`}
              </span>
            )}
          </div>
        </div>

        {/* Picks */}
        <div className="space-y-1">
          {cats.map((cat, i) => {
            const isCorrect = pred.is_processed && cat.actual !== null && cat.predicted === cat.actual;
            const isWrong = pred.is_processed && cat.actual !== null && cat.predicted !== cat.actual;
            const sameAsMe = !pred.is_me && myPred ? isSamePick(cat, myPred, match, i) : false;
            const CatIcon = cat.icon;
            return (
              <div
                key={cat.label}
                className={cn(
                  'flex items-center gap-2 text-xs rounded px-1 -mx-1',
                  sameAsMe && 'bg-primary/5',
                )}
              >
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

function ConsensusStrip({ predictions, match }: { predictions: FriendPrediction[]; match: MatchInfo }) {
  const total = predictions.length;

  const categories = [
    {
      label: 'Winner',
      picks: predictions.map(p => p.predicted_winner.short_name),
    },
    {
      label: `Runs (${match.team_1.short_name})`,
      picks: predictions.map(p => p.predicted_most_runs_team1_player.name),
    },
    {
      label: `Runs (${match.team_2.short_name})`,
      picks: predictions.map(p => p.predicted_most_runs_team2_player.name),
    },
    {
      label: `Wkts (${match.team_1.short_name})`,
      picks: predictions.map(p => p.predicted_most_wickets_team1_player.name),
    },
    {
      label: `Wkts (${match.team_2.short_name})`,
      picks: predictions.map(p => p.predicted_most_wickets_team2_player.name),
    },
    {
      label: 'POM',
      picks: predictions.map(p => p.predicted_pom_player.name),
    },
  ];

  const consensus = categories.map(cat => {
    const counts: Record<string, number> = {};
    cat.picks.forEach(pick => { counts[pick] = (counts[pick] || 0) + 1; });
    const [topPick, topCount] = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    return { label: cat.label, topPick, count: topCount };
  });

  return (
    <Card className="border-border/50 bg-muted/30">
      <CardContent className="p-3 space-y-1.5">
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-2">Group consensus</p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
          {consensus.map(({ label, topPick, count }) => (
            <div key={label} className="space-y-0.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-muted-foreground">{label}</span>
                <span className="text-[10px] text-muted-foreground">{count}/{total}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="flex-1 h-1 rounded-full bg-border overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary/60"
                    style={{ width: `${(count / total) * 100}%` }}
                  />
                </div>
                <span className="text-[11px] font-medium truncate max-w-[5rem]">{topPick}</span>
              </div>
            </div>
          ))}
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
        <Skeleton className="h-24 w-full" />
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
  const myPred = predictions.find(p => p.is_me) ?? null;

  return (
    <div className="container-mobile py-6 space-y-4 pb-24">
      {/* Back */}
      <Link href="/predictions" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary">
        <ChevronLeft className="h-4 w-4" /> Back to Predictions
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold">
          {match ? `${match.team_1.short_name} vs ${match.team_2.short_name}` : "Friends' Picks"}
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

      {predictions.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-muted-foreground">No one in this league has predicted this match yet.</p>
        </Card>
      ) : (
        <>
          {/* Group consensus */}
          {predictions.length >= 2 && match && (
            <ConsensusStrip predictions={predictions} match={match} />
          )}

          {/* Cards */}
          <div className="space-y-3">
            {predictions.map((pred, i) => (
              <PredictionCard key={i} pred={pred} match={match!} myPred={myPred} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
