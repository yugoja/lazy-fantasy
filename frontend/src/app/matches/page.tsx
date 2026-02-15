'use client';

import { useEffect, useState } from 'react';
import { getMatches, getMyPredictions } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { MatchCard } from '@/components/MatchCard';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface Match {
  id: number;
  team_1: { id: number; name: string; short_name: string; flag_code?: string };
  team_2: { id: number; name: string; short_name: string; flag_code?: string };
  start_time: string;
  status: string;
  venue?: string;
}

export default function MatchesPage() {
  const { isAuthenticated } = useAuth();
  const [matches, setMatches] = useState<Match[]>([]);
  const [predictedMatchIds, setPredictedMatchIds] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadMatches();
  }, [isAuthenticated]);

  const loadMatches = async () => {
    try {
      const [matchesResult, predictionsResult] = await Promise.allSettled([
        getMatches(),
        isAuthenticated ? getMyPredictions() : Promise.resolve([]),
      ]);
      if (matchesResult.status === 'fulfilled') {
        setMatches(matchesResult.value);
      } else {
        setError('Failed to load matches');
      }
      if (predictionsResult.status === 'fulfilled') {
        setPredictedMatchIds(new Set(predictionsResult.value.map(p => p.match_id)));
      }
    } catch {
      setError('Failed to load matches');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container-mobile py-6 space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-44" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container-mobile py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">All Matches</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Make your predictions before the match starts
        </p>
      </div>

      {/* Error */}
      {error && (
        <Card className="p-3 border-destructive/50 bg-destructive/10">
          <p className="text-sm text-destructive">{error}</p>
        </Card>
      )}

      {/* Match List */}
      {!error && matches.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-muted-foreground">No matches available right now</p>
          <p className="text-xs text-muted-foreground mt-1">Check back later for new matches</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {matches.map((match) => (
            <MatchCard
              key={match.id}
              id={match.id}
              team1={match.team_1}
              team2={match.team_2}
              startTime={match.start_time}
              status={match.status as 'SCHEDULED' | 'LIVE' | 'COMPLETED'}
              venue={match.venue}
              hasPredicted={predictedMatchIds.has(match.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
