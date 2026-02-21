'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '@/lib/auth';
import { getMatches, getMyPredictions, getMyPredictionsDetailed, PredictionDetail } from '@/lib/api';
import { MatchCard } from '@/components/MatchCard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Trophy, Target, Star, Check, X } from 'lucide-react';
import { cn, getFlagUrl } from '@/lib/utils';

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
      const [matchesData, predictionsData, detailedData] = await Promise.allSettled([
        getMatches(),
        getMyPredictions(),
        getMyPredictionsDetailed(),
      ]);
      if (matchesData.status === 'fulfilled') setMatches(matchesData.value);
      if (predictionsData.status === 'fulfilled') setPredictions(predictionsData.value);
      if (detailedData.status === 'fulfilled') setDetailedPredictions(detailedData.value);
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
  const completed = matches.filter(m => m.status === 'COMPLETED');

  const renderMatches = (filteredMatches: Match[], showPoints = false) => {
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
          return (
            <div key={match.id}>
              <MatchCard
                id={match.id}
                team1={match.team_1}
                team2={match.team_2}
                startTime={match.start_time}
                status={match.status as 'SCHEDULED' | 'LIVE' | 'COMPLETED'}
                venue={match.venue}
                hasPredicted={!!prediction}
                pointsEarned={showPoints && prediction?.is_processed ? prediction.points_earned : undefined}
                lineupAnnounced={match.lineup_announced}
              />
            </div>
          );
        })}
      </div>
    );
  };

  const totalPoints = detailedPredictions
    .filter(p => p.is_processed)
    .reduce((sum, p) => sum + p.points_earned, 0);

  const renderPredictionHistory = () => {
    if (detailedPredictions.length === 0) {
      return (
        <Card className="p-8 text-center space-y-2">
          <p className="text-sm text-muted-foreground">No predictions yet</p>
          <p className="text-xs text-muted-foreground">Pick a match from the Upcoming tab to get started!</p>
        </Card>
      );
    }

    return (
      <div className="space-y-3">
        {/* Points Summary */}
        {detailedPredictions.some(p => p.is_processed) && (
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-[10px] text-muted-foreground">Total Points Earned</p>
                <p className="text-2xl font-bold">{totalPoints}</p>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-muted-foreground">Predictions</p>
                <p className="text-lg font-bold">{detailedPredictions.length}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Prediction Cards */}
        {detailedPredictions.map((pred) => {
          const flag1 = getFlagUrl(pred.team_1.short_name);
          const flag2 = getFlagUrl(pred.team_2.short_name);
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
              label: 'Most Runs',
              icon: Target,
              predicted: pred.predicted_most_runs_player.name,
              actual: pred.actual_most_runs_player?.name,
              pts: 20,
              color: 'text-blue-400',
            },
            {
              label: 'Most Wickets',
              icon: Target,
              predicted: pred.predicted_most_wickets_player.name,
              actual: pred.actual_most_wickets_player?.name,
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
            <Link key={pred.id} href={`/matches/${pred.match_id}`}>
              <Card className="border-border bg-card hover:border-primary/30 transition-colors">
                <CardContent className="p-4 space-y-3">
                  {/* Match header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {flag1 && (
                        <Image src={flag1} alt="" width={24} height={16} className="h-4 w-6 object-cover rounded-sm" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                      )}
                      <span className="text-sm font-semibold">
                        {pred.team_1.short_name} vs {pred.team_2.short_name}
                      </span>
                      {flag2 && (
                        <Image src={flag2} alt="" width={24} height={16} className="h-4 w-6 object-cover rounded-sm" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
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
                          {isCorrect && <Check className="h-3.5 w-3.5 text-green-400 shrink-0" />}
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
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    );
  };

  return (
    <div className="container-mobile py-6 space-y-6 pb-24">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Match Predictions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Pick a match to make your predictions.
        </p>
      </div>

      {/* Error */}
      {loadError && (
        <Card className="p-3 border-destructive/50 bg-destructive/10">
          <p className="text-sm text-destructive">{loadError}</p>
        </Card>
      )}

      {/* Tabs */}
      <Tabs defaultValue="upcoming" className="w-full">
        <TabsList className="w-full">
          <TabsTrigger value="upcoming" className="flex-1">
            Upcoming
          </TabsTrigger>
          <TabsTrigger value="my-picks" className="flex-1">
            My Picks ({detailedPredictions.length})
          </TabsTrigger>
          <TabsTrigger value="completed" className="flex-1">
            Done ({completed.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming" className="mt-4">
          {renderMatches(upcoming)}
        </TabsContent>

        <TabsContent value="my-picks" className="mt-4">
          {renderPredictionHistory()}
        </TabsContent>

        <TabsContent value="completed" className="mt-4">
          {renderMatches(completed, true)}
        </TabsContent>
      </Tabs>
    </div>
  );
}
