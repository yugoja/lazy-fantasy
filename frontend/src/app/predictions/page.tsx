'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { getMatches, getMyPredictions } from '@/lib/api';
import { MatchCard } from '@/components/MatchCard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';

interface Match {
  id: number;
  team_1: { id: number; name: string; short_name: string; flag_code?: string };
  team_2: { id: number; name: string; short_name: string; flag_code?: string };
  start_time: string;
  status: string;
  venue?: string;
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
  const [isLoading, setIsLoading] = useState(true);

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
      const [matchesData, predictionsData] = await Promise.all([
        getMatches(),
        getMyPredictions(),
      ]);
      setMatches(matchesData);
      setPredictions(predictionsData);
    } catch (err) {
      console.error('Failed to load data', err);
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

  const predictionMatchIds = new Set(predictions.map(p => p.match_id));
  const predictionByMatch = new Map(predictions.map(p => [p.match_id, p]));

  const now = new Date();
  const upcoming = matches.filter(m => m.status === 'upcoming' || new Date(m.start_time) > now);
  const live = matches.filter(m => m.status === 'live');
  const completed = matches.filter(m => m.status === 'completed');

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
            <div key={match.id} className="relative">
              <MatchCard
                id={match.id}
                team1={match.team_1}
                team2={match.team_2}
                startTime={match.start_time}
                status={match.status.toUpperCase() as 'UPCOMING' | 'LIVE' | 'COMPLETED'}
                venue={match.venue}
              />
              {prediction && (
                <div className="absolute top-3 right-3">
                  {showPoints && prediction.is_processed ? (
                    <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 text-xs">
                      +{prediction.points_earned} pts
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-xs">
                      Predicted
                    </Badge>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Match Predictions</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Pick a match to make your predictions.
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="upcoming" className="w-full">
        <TabsList className="w-full">
          <TabsTrigger value="upcoming" className="flex-1">
            Upcoming ({upcoming.length})
          </TabsTrigger>
          <TabsTrigger value="live" className="flex-1">
            Live ({live.length})
          </TabsTrigger>
          <TabsTrigger value="completed" className="flex-1">
            Done ({completed.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming" className="mt-4">
          {renderMatches(upcoming)}
        </TabsContent>

        <TabsContent value="live" className="mt-4">
          {renderMatches(live)}
        </TabsContent>

        <TabsContent value="completed" className="mt-4">
          {renderMatches(completed, true)}
        </TabsContent>
      </Tabs>
    </div>
  );
}
