'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getMatches, getMyPredictions, getMyPredictionsDetailed, getMyLeagues, PredictionDetail } from '@/lib/api';
import { MatchCard } from '@/components/MatchCard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Trophy, Target, Star, Check, X, Flag, Zap, Users } from 'lucide-react';
import { cn, getTeamLogoUrl } from '@/lib/utils';
import { ShareButton } from '@/components/ShareButton';
import { shareWithCard } from '@/lib/share';
import { generateUpcomingCard, generateResultCard } from '@/lib/share-card';

interface Match {
  id: number;
  team_1: { id: number; name: string; short_name: string; flag_code?: string };
  team_2: { id: number; name: string; short_name: string; flag_code?: string };
  start_time: string;
  status: string;
  venue?: string;
  lineup_announced: boolean;
}

interface Prediction {
  id: number;
  match_id: number;
  points_earned: number;
  is_processed: boolean;
}

export default function PredictionsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [matches, setMatches] = useState<Match[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [detailedPredictions, setDetailedPredictions] = useState<PredictionDetail[]>([]);
  const [leagues, setLeagues] = useState<Array<{ id: number; name: string }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated]);

  const loadData = async () => {
    try {
      const [matchesData, predictionsData, detailedData, leaguesData] = await Promise.allSettled([
        getMatches(),
        getMyPredictions(),
        getMyPredictionsDetailed(),
        getMyLeagues(),
      ]);
      if (matchesData.status === 'fulfilled') setMatches(matchesData.value);
      if (predictionsData.status === 'fulfilled') setPredictions(predictionsData.value);
      if (detailedData.status === 'fulfilled') setDetailedPredictions(detailedData.value);
      if (leaguesData.status === 'fulfilled') setLeagues(leaguesData.value);
    } catch {
      setLoadError('Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-56" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-10 w-full" />
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  const predictionByMatch = new Map(predictions.map(p => [p.match_id, p]));

  const now = new Date();
  const upcoming = matches.filter(m => m.status === 'SCHEDULED' && new Date(m.start_time) > now);
  const todayStart = new Date(); todayStart.setHours(0, 0, 0, 0);
  const ongoing = matches.filter(m => m.status !== 'COMPLETED' && new Date(m.start_time) <= now && new Date(m.start_time) >= todayStart);
  const detailedByMatchId = new Map(detailedPredictions.map(p => [p.match_id, p]));

  const renderMatches = (filteredMatches: Match[]) => {
    if (filteredMatches.length === 0) {
      return (
        <Card className="p-8 text-center">
          <p className="text-sm text-muted-foreground">No matches found</p>
        </Card>
      );
    }

    return (
      <div className="space-y-3">
        {filteredMatches.map((match) => {
          const prediction = predictionByMatch.get(match.id);
          const hasPredicted = !!prediction;
          return (
            <div key={match.id} className="space-y-2">
              <MatchCard
                id={match.id}
                team1={match.team_1}
                team2={match.team_2}
                startTime={match.start_time}
                status={match.status as 'SCHEDULED' | 'LIVE' | 'COMPLETED'}
                venue={match.venue}
                hasPredicted={hasPredicted}
                lineupAnnounced={match.lineup_announced}
              />
              {hasPredicted && (
                <ShareButton
                  onClick={async () => {
                    const image = await generateUpcomingCard({
                      team1: match.team_1.short_name,
                      team2: match.team_2.short_name,
                      startTime: match.start_time,
                      venue: match.venue,
                    });
                    await shareWithCard({
                      text: buildUpcomingShareText(match.team_1.short_name, match.team_2.short_name, match.start_time),
                      title: `${match.team_1.short_name} vs ${match.team_2.short_name}`,
                      image,
                    });
                  }}
                >
                  Nudge your group
                </ShareButton>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const totalPoints = detailedPredictions
    .filter(p => p.is_processed)
    .reduce((sum, p) => sum + p.points_earned, 0);

  const formatCountdown = (startTime: string): string => {
    const diff = new Date(startTime).getTime() - Date.now();
    if (diff <= 0) return 'soon';
    const totalMins = Math.floor(diff / 60000);
    const hours = Math.floor(totalMins / 60);
    const mins = totalMins % 60;
    if (hours > 0 && mins > 0) return `${hours}h ${mins}m`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
    return `${mins} min`;
  };

  const buildUpcomingShareText = (team1: string, team2: string, startTime: string): string => {
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app';
    return [
      `🏏 ${team1} vs ${team2} — predictions are open!`,
      '',
      `I've locked in my call. Have you? ⏰`,
      `Closes in ${formatCountdown(startTime)} 👇`,
      `${appUrl}/predictions`,
    ].join('\n');
  };

  const buildResultShareText = (pred: PredictionDetail): string => {
    const winner = pred.actual_winner?.short_name;
    const loser = winner === pred.team_1.short_name ? pred.team_2.short_name : pred.team_1.short_name;
    const cats = [
      { label: 'Winner', ok: pred.actual_winner && pred.predicted_winner.short_name === pred.actual_winner.short_name },
      { label: `Runs (${pred.team_1.short_name})`, ok: pred.actual_most_runs_team1_player && pred.predicted_most_runs_team1_player.name === pred.actual_most_runs_team1_player.name },
      { label: `Runs (${pred.team_2.short_name})`, ok: pred.actual_most_runs_team2_player && pred.predicted_most_runs_team2_player.name === pred.actual_most_runs_team2_player.name },
      { label: `Wickets (${pred.team_1.short_name})`, ok: pred.actual_most_wickets_team1_player && pred.predicted_most_wickets_team1_player.name === pred.actual_most_wickets_team1_player.name },
      { label: `Wickets (${pred.team_2.short_name})`, ok: pred.actual_most_wickets_team2_player && pred.predicted_most_wickets_team2_player.name === pred.actual_most_wickets_team2_player.name },
      { label: 'POM', ok: pred.actual_pom_player && pred.predicted_pom_player.name === pred.actual_pom_player.name },
    ];
    const scorecard = cats.map(c => `${c.ok ? '✅' : '❌'} ${c.label}`).join('\n');
    const correctCount = cats.filter(c => c.ok).length;
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://lazyfantasy.app';
    return [
      `🏏 ${winner} beat ${loser} — results are in!`,
      '',
      `I got ${pred.points_earned}/140 on Lazy Fantasy (${correctCount}/6 correct) 🎯`,
      '',
      scorecard,
      '',
      `Who else predicted? Drop your score 👇`,
      `${appUrl}/predictions`,
    ].join('\n');
  };

  const friendsPicksLink = (matchId: number) => {
    if (leagues.length === 0) return null;
    return `/leagues/${leagues[0].id}/match/${matchId}`;
  };

  const renderDetailedCard = (pred: PredictionDetail) => {
    const flag1 = getTeamLogoUrl(pred.team_1.short_name);
    const flag2 = getTeamLogoUrl(pred.team_2.short_name);
    const isProcessed = pred.is_processed;

    const categories = [
      {
        label: 'Winner',
        icon: Trophy,
        predicted: pred.predicted_winner.short_name,
        actual: pred.actual_winner?.short_name,
        pts: 10,
        color: 'text-primary',
      },
      {
        label: `Runs (${pred.team_1.short_name})`,
        icon: Target,
        predicted: pred.predicted_most_runs_team1_player.name,
        actual: pred.actual_most_runs_team1_player?.name,
        pts: 20,
        color: 'text-blue-400',
      },
      {
        label: `Runs (${pred.team_2.short_name})`,
        icon: Target,
        predicted: pred.predicted_most_runs_team2_player.name,
        actual: pred.actual_most_runs_team2_player?.name,
        pts: 20,
        color: 'text-blue-400',
      },
      {
        label: `Wkts (${pred.team_1.short_name})`,
        icon: Target,
        predicted: pred.predicted_most_wickets_team1_player.name,
        actual: pred.actual_most_wickets_team1_player?.name,
        pts: 20,
        color: 'text-green-400',
      },
      {
        label: `Wkts (${pred.team_2.short_name})`,
        icon: Target,
        predicted: pred.predicted_most_wickets_team2_player.name,
        actual: pred.actual_most_wickets_team2_player?.name,
        pts: 20,
        color: 'text-green-400',
      },
      {
        label: 'POM',
        icon: Star,
        predicted: pred.predicted_pom_player.name,
        actual: pred.actual_pom_player?.name,
        pts: 50,
        color: 'text-yellow-400',
      },
    ];

    return (
      <Card key={pred.id} className="border-border bg-card">
        <CardContent className="p-4 space-y-3">
          {/* Match header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {flag1 && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={flag1} alt="" width={20} height={20} className="h-5 w-5 object-contain" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
              )}
              <span className="text-sm font-semibold">
                {pred.team_1.short_name} vs {pred.team_2.short_name}
              </span>
              {flag2 && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={flag2} alt="" width={20} height={20} className="h-5 w-5 object-contain" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
              )}
            </div>
            {isProcessed ? (
              <Badge variant={pred.points_earned > 0 ? 'default' : 'secondary'} className="text-[10px]">
                +{pred.points_earned} pts
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px]">Pending</Badge>
            )}
          </div>

          {/* Date */}
          <p className="text-[10px] text-muted-foreground">
            {new Date(pred.start_time).toLocaleDateString('en-US', {
              month: 'short', day: 'numeric',
            })}
            {' '}&middot; {pred.status}
          </p>

          {/* Prediction breakdown */}
          <div className="space-y-2">
            {categories.map((cat) => {
              const isCorrect = isProcessed && cat.actual && cat.predicted === cat.actual;
              const isWrong = isProcessed && cat.actual && cat.predicted !== cat.actual;

              return (
                <div key={cat.label} className="flex items-center gap-2 text-xs">
                  <cat.icon className={cn('h-3 w-3 shrink-0', cat.color)} />
                  <span className="text-muted-foreground w-16 shrink-0">{cat.label}</span>
                  <span className={cn(
                    'flex-1 truncate font-medium',
                    isCorrect && 'text-green-400',
                    isWrong && 'text-muted-foreground line-through',
                  )}>
                    {cat.predicted}
                  </span>
                  {isCorrect && (
                    <div className="flex items-center gap-1 shrink-0">
                      <Check className="h-3.5 w-3.5 text-green-400" />
                      <span className="text-[10px] font-semibold text-green-400">+{cat.pts}</span>
                    </div>
                  )}
                  {isWrong && (
                    <div className="flex items-center gap-1 shrink-0">
                      <X className="h-3.5 w-3.5 text-red-400" />
                      <span className="text-[10px] text-muted-foreground truncate max-w-20">{cat.actual}</span>
                    </div>
                  )}
                  {!isProcessed && (
                    <span className="text-[10px] text-muted-foreground shrink-0">+{cat.pts}</span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Friends' picks link — shown for all locked matches */}
          {friendsPicksLink(pred.match_id) && (
            <Link
              href={friendsPicksLink(pred.match_id)!}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors mt-1"
            >
              <Users className="h-3.5 w-3.5" />
              Friends&apos; picks
            </Link>
          )}

          {/* Share — only shown once results are processed */}
          {isProcessed && (
            <ShareButton
              className="mt-1"
              onClick={async () => {
                const categories = [
                  { label: 'Winner', correct: !!(pred.actual_winner && pred.predicted_winner.short_name === pred.actual_winner.short_name) },
                  { label: `Runs (${pred.team_1.short_name})`, correct: !!(pred.actual_most_runs_team1_player && pred.predicted_most_runs_team1_player.name === pred.actual_most_runs_team1_player.name) },
                  { label: `Runs (${pred.team_2.short_name})`, correct: !!(pred.actual_most_runs_team2_player && pred.predicted_most_runs_team2_player.name === pred.actual_most_runs_team2_player.name) },
                  { label: `Wkts (${pred.team_1.short_name})`, correct: !!(pred.actual_most_wickets_team1_player && pred.predicted_most_wickets_team1_player.name === pred.actual_most_wickets_team1_player.name) },
                  { label: `Wkts (${pred.team_2.short_name})`, correct: !!(pred.actual_most_wickets_team2_player && pred.predicted_most_wickets_team2_player.name === pred.actual_most_wickets_team2_player.name) },
                  { label: 'POM', correct: !!(pred.actual_pom_player && pred.predicted_pom_player.name === pred.actual_pom_player.name) },
                ];
                const image = await generateResultCard({
                  team1: pred.team_1.short_name,
                  team2: pred.team_2.short_name,
                  winner: pred.actual_winner?.short_name || '?',
                  points: pred.points_earned,
                  categories,
                });
                await shareWithCard({
                  text: buildResultShareText(pred),
                  title: `${pred.team_1.short_name} vs ${pred.team_2.short_name} — ${pred.points_earned} pts`,
                  image,
                });
              }}
            >
              Share Score
            </ShareButton>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderPredictionHistory = () => {
    if (detailedPredictions.length === 0) {
      return (
        <Card className="p-8 text-center space-y-2">
          <p className="text-sm text-muted-foreground">No predictions yet</p>
          <p className="text-xs text-muted-foreground">Pick a match from the Upcoming tab to get started!</p>
        </Card>
      );
    }

    const processed = detailedPredictions.filter(p => p.is_processed);
    const maxPoints = processed.length * 140;

    const categoryStats = [
      {
        label: 'Winner',
        icon: Trophy,
        color: 'text-primary',
        bgColor: 'bg-primary',
        pts: 10,
        correct: processed.filter(p => p.actual_winner && p.predicted_winner.short_name === p.actual_winner.short_name).length,
      },
      {
        label: 'Runs (T1)',
        icon: Target,
        color: 'text-blue-400',
        bgColor: 'bg-blue-400',
        pts: 20,
        correct: processed.filter(p => p.actual_most_runs_team1_player && p.predicted_most_runs_team1_player.name === p.actual_most_runs_team1_player.name).length,
      },
      {
        label: 'Runs (T2)',
        icon: Target,
        color: 'text-blue-300',
        bgColor: 'bg-blue-300',
        pts: 20,
        correct: processed.filter(p => p.actual_most_runs_team2_player && p.predicted_most_runs_team2_player.name === p.actual_most_runs_team2_player.name).length,
      },
      {
        label: 'Wkts (T1)',
        icon: Target,
        color: 'text-green-400',
        bgColor: 'bg-green-400',
        pts: 20,
        correct: processed.filter(p => p.actual_most_wickets_team1_player && p.predicted_most_wickets_team1_player.name === p.actual_most_wickets_team1_player.name).length,
      },
      {
        label: 'Wkts (T2)',
        icon: Target,
        color: 'text-green-300',
        bgColor: 'bg-green-300',
        pts: 20,
        correct: processed.filter(p => p.actual_most_wickets_team2_player && p.predicted_most_wickets_team2_player.name === p.actual_most_wickets_team2_player.name).length,
      },
      {
        label: 'POM',
        icon: Star,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-400',
        pts: 50,
        correct: processed.filter(p => p.actual_pom_player && p.predicted_pom_player.name === p.actual_pom_player.name).length,
      },
    ];

    const totalCorrect = categoryStats.reduce((s, c) => s + c.correct, 0);
    const totalPossibleCorrect = processed.length * 6;

    return (
      <div className="space-y-4">
        {/* Points Summary */}
        {processed.length > 0 && (
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="p-4 space-y-4">
              {/* Total score */}
              <div className="flex items-end justify-between">
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Total Points</p>
                  <p className="text-3xl font-bold tracking-tight">{totalPoints}<span className="text-base font-normal text-muted-foreground">/{maxPoints}</span></p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Accuracy</p>
                  <p className="text-lg font-bold">{totalCorrect}/{totalPossibleCorrect}</p>
                </div>
              </div>

              {/* Overall progress bar */}
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: maxPoints > 0 ? `${(totalPoints / maxPoints) * 100}%` : '0%' }}
                />
              </div>

              {/* Per-category breakdown */}
              <div className="grid grid-cols-2 gap-3">
                {categoryStats.map((cat) => {
                  const pct = processed.length > 0 ? (cat.correct / processed.length) * 100 : 0;
                  return (
                    <div key={cat.label} className="space-y-1.5">
                      <div className="flex items-center gap-1.5">
                        <cat.icon className={cn('h-3 w-3', cat.color)} />
                        <span className="text-[10px] text-muted-foreground">{cat.label}</span>
                        <span className="text-[10px] font-semibold ml-auto">{cat.correct}/{processed.length}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className={cn('h-full rounded-full transition-all', cat.bgColor)}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Prediction Cards */}
        {detailedPredictions.map((pred) => renderDetailedCard(pred))}
      </div>
    );
  };

  return (
    <div className="container-mobile py-6 space-y-6 pb-24">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Match Predictions</h1>
          <p className="text-sm text-muted-foreground mt-1">Pick a match to make your predictions.</p>
        </div>
      </div>

      {loadError && (
        <Card className="p-3 border-destructive/50 bg-destructive/10">
          <p className="text-sm text-destructive">{loadError}</p>
        </Card>
      )}

      <Tabs defaultValue="upcoming" className="w-full">
        <TabsList className="w-full">
          <TabsTrigger value="upcoming" className="flex-1">Upcoming</TabsTrigger>
          <TabsTrigger value="live" className="flex-1">Live ({ongoing.length})</TabsTrigger>
          <TabsTrigger value="done" className="flex-1">Done ({detailedPredictions.length})</TabsTrigger>
        </TabsList>
        <TabsContent value="upcoming" className="mt-4">{renderMatches(upcoming)}</TabsContent>
        <TabsContent value="live" className="mt-4">
          {ongoing.length === 0 ? (
            <Card className="p-8 text-center"><p className="text-sm text-muted-foreground">No live matches right now</p></Card>
          ) : (
            <div className="space-y-4">
              {ongoing.map((match) => {
                const pred = detailedByMatchId.get(match.id);
                const link = friendsPicksLink(match.id);
                if (!pred) {
                  return (
                    <div key={match.id} className="space-y-2">
                      <MatchCard id={match.id} team1={match.team_1} team2={match.team_2} startTime={match.start_time} status={match.status as 'SCHEDULED' | 'LIVE' | 'COMPLETED'} venue={match.venue} hasPredicted={!!predictionByMatch.get(match.id)} lineupAnnounced={match.lineup_announced} />
                      {link && (
                        <Link href={link} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors px-1">
                          <Users className="h-3.5 w-3.5" />
                          Friends&apos; picks
                        </Link>
                      )}
                    </div>
                  );
                }
                return renderDetailedCard(pred);
              })}
            </div>
          )}
        </TabsContent>
        <TabsContent value="done" className="mt-4">{renderPredictionHistory()}</TabsContent>
      </Tabs>
    </div>
  );
}
