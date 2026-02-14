'use client';

import { useEffect, useState } from 'react';
import { getMatches } from '@/lib/api';
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
  const [matches, setMatches] = useState<Match[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadMatches();
  }, []);

  const loadMatches = async () => {
    try {
      const data = await getMatches();
      setMatches(data);
    } catch (err) {
      console.error('Failed to load matches', err);
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

      {/* Match List */}
      {matches.length === 0 ? (
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
              status={match.status.toUpperCase() as 'UPCOMING' | 'LIVE' | 'COMPLETED'}
              venue={match.venue}
            />
          ))}
        </div>
      )}
    </div>
  );
}
